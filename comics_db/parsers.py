"""
Different parsers for getting comix info
"""
import datetime
import inspect
import re

import boto3
import botocore
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db import Error
from django.utils import timezone

from comics_db import models as comics_models
from comics_db.models import ParserRun, ParserRunDetail, CloudFilesParserRunDetail
from comicsdb import settings


class ParserError(Exception):
    """
    Root Exception class for this module
    """
    STATUS_CODE = ""

    def __init__(self, message, detail=""):
        self.message = message
        self.detail = detail


class InvalidParserImplementationError(ParserError):
    STATUS_CODE = "INVALID_PARSER"


class RuntimeParserError(ParserError):
    STATUS_CODE = "CRITICAL_ERROR"


class BaseParser:
    """
    Base class for parsers.

    Handles creating run log and common parameters for all parsers.
    Specific parsers should implement _process method and override parser_code and run_detail_model fields
    """
    PARSER_CODE = "BASE"  # Parser code for linking log to specific parser type
    RUN_DETAIL_MODEL = ParserRunDetail  # Model for saving parser detail logs

    def __init__(self):
        self._parser_run = None
        self._data = None

    @property
    def _items_count(self):
        """
        Count items to be processed by parser. Should be overridden in specific parser classes
        :return: items count
        """
        return None

    def _prepare(self):
        """
        Prepare data. Should be overridden in specific parser classes

        Preparing data i.e. retrieve data that will be parsed from server or select object for parse from DB
        :return: None
        """

    def _process(self):
        """
        Method for parser work. Should be overridden in specific parser classes

        If critical error happens during processing, method should raise RuntimeParserError.
        Critical error - error which prevent parser from continue work.
        Errors which happens during processing one isolated item are not critical and should be handled within method
        (e.g. marked as error in log)

        :return: Run result boolean (True - success, False - ended with errors)
        """
        return True

    def run(self):
        """
        Main method for running parser.

        Handles creating record in parser run log, checks correctness of specific implementation and handles
        unrecoverable errors.
        :return: Run result boolean (True - success, False - error)
        """
        try:
            # Initializing Run
            self._parser_run = ParserRun()

            # Checking parser code
            # Parser code is overridden
            if self.PARSER_CODE == BaseParser.PARSER_CODE:
                raise InvalidParserImplementationError(
                    '{0.__class__} Parser code should be overridden in implementation'.format(self.PARSER_CODE))

            # Parser code in valid parser codes list
            if self.PARSER_CODE not in (x[0] for x in ParserRun.PARSER_CHOICES):
                raise InvalidParserImplementationError(
                    '{0.__class__} Parser code "{0.PARSER_CODE}" not in ParserRun.PARSER_CHOICES'.format(self))

            self._parser_run.parser = self.PARSER_CODE

            # Checking Run Detail Model
            # Run Detail Model is a class
            if not inspect.isclass(self.RUN_DETAIL_MODEL):
                raise InvalidParserImplementationError(
                    '{0.__class__} Run Detail Model should be a class'.format(self))

            # Run Detail Model is overridden
            if self.RUN_DETAIL_MODEL == ParserRunDetail:
                raise InvalidParserImplementationError(
                    '{0.__class__} Run Detail Model should be overridden in implementation'.format(self))

            # Run Detail Model is a subclass of BaseParser.RUN_DETAIL_MODEL
            if not issubclass(self.RUN_DETAIL_MODEL, BaseParser.RUN_DETAIL_MODEL):
                raise InvalidParserImplementationError(
                    '{0.__class__} Run Detail Model should be a subclass of BaseParser.RUN_DETAIL_MODEL'.format(self))

            # Preparing data, filling items count and saving Run log record to table
            self._prepare()
            self._parser_run.items_count = self._items_count
            self._parser_run.save()

            # Starting processing
            process_result = self._process()

            # Setting result status and ending work
            if process_result:
                self._parser_run.status = "SUCCESS"
            else:
                self._parser_run.status = "ENDED_WITH_ERRORS"
            self._parser_run.end = timezone.now()
            self._parser_run.save()

            return True

        except ParserError as err:
            self._parser_run.status = err.STATUS_CODE
            self._parser_run.error = err.message
            self._parser_run.error_detail = err.detail
            self._parser_run.end = timezone.now()
            self._parser_run.save()
            return False
        except Exception as err:
            self._parser_run.status = "INVALID_PARSER"
            self._parser_run.error = "{0} Unhandled error in method run".format(BaseParser)
            self._parser_run.error_detail = err
            self._parser_run.end = timezone.now()
            self._parser_run.save()
            return False


class CloudFilesParser(BaseParser):
    PARSER_CODE = "CLOUD_FILES"
    RUN_DETAIL_MODEL = CloudFilesParserRunDetail
    _REGEX = re.compile(r"^content/"
                        r"(?P<publisher>.+?)/"
                        r"(?P<universe>.+?)/"
                        r"(?P<year>\d+?)/"
                        r"(?P<title_type>.+?)/"
                        r"(?:(?P<title>.+?)\/)?"
                        r"(?P<issue_name>[^#]+?(?:#(?P<number>-?[.0-9]+))?[^#]*)\.(?:cbr|cbt|cbz)$",
                        re.IGNORECASE)
    _FILE_REGEX = re.compile(r"\.cb(r|z|t)", re.IGNORECASE)

    def _prepare(self):
        try:
            session = boto3.session.Session()
            s3 = session.resource('s3', region_name=settings.DO_REGION_NAME,
                                  endpoint_url=settings.DO_ENDPOINT_URL,
                                  aws_access_key_id=settings.DO_KEY_ID,
                                  aws_secret_access_key=settings.DO_SECRET_ACCESS_KEY)
            bucket = s3.Bucket(settings.DO_STORAGE_BUCKET_NAME)
            bucket_comics = bucket.objects.filter(Prefix="content/Marvel/Earth-616/2004")
            self._data = [x.key for x in bucket_comics if self._FILE_REGEX.search(x.key)]
            self._parser_run.processed = 0

        except botocore.exceptions.ConnectionError:
            raise RuntimeParserError("Could not establish connection to DO cloud")
        except botocore.exception.ClientError as err:
            raise RuntimeParserError("boto3 client error while preparing data", err.msg)
        except Exception as err:
            raise RuntimeParserError("Error while preparing data", err)

    @property
    def _items_count(self):
        if self._data:
            return len(self._data)
        else:
            return 0

    def _process(self):
        run_detail = None
        try:
            has_errors = False
            for file_key in self._data:
                # Creating run detail log entry
                run_detail = self.RUN_DETAIL_MODEL(parser_run=self._parser_run,
                                                   file_key=file_key,
                                                   regex=self._REGEX.pattern, )
                run_detail.save()

                # Parsing file key
                match = self._REGEX.search(file_key)
                if not match:
                    # Not matched. Saving error to log and closing log entry
                    run_detail.end_with_error("File key does not match regular expression")
                    has_errors = True
                else:
                    # Matched. Saving regex match groups and starting filling issue info in DB
                    info = match.groupdict()
                    run_detail.groups = str(info)
                    try:
                        # Getting or creating Publisher
                        publisher, created = comics_models.Publisher.objects.get_or_create(name=info['publisher'])
                        if created:
                            publisher.save()

                        # Getting or creating Universe
                        universe, created = comics_models.Universe.objects.get_or_create(name=info['universe'],
                                                                                         publisher=publisher)
                        if created:
                            universe.save()

                        # Getting or creating Title type
                        title_type, created = comics_models.TitleType.objects.get_or_create(name=info['title_type'])
                        if created:
                            title_type.save()

                        # Getting or creating Title
                        title, created = comics_models.Title.objects.get_or_create(name=(info['title']
                                                                                         or info['issue_name']),
                                                                                   publisher=publisher,
                                                                                   universe=universe,
                                                                                   title_type=title_type)
                        if created:
                            title.save()
                        # Getting publish date
                        publish_date = datetime.date(int(info['year']), 1, 1)

                        # Getting or creating issue
                        issue, created = comics_models.Issue.objects.get_or_create(name=info['issue_name'],
                                                                                   number=info['number'],
                                                                                   title=title,
                                                                                   publish_date=publish_date,
                                                                                   defaults={
                                                                                       'publish_date': publish_date
                                                                                   })
                        if created:
                            issue.link = file_key
                            issue.save()

                        run_detail.issue = issue
                        run_detail.created = created
                        run_detail.end_with_success()

                    except KeyError as err:
                        run_detail.end_with_error("Match object has no group named \"{0}\"".format(err))
                        has_errors = True
                    except MultipleObjectsReturned as err:
                        run_detail.end_with_error("Multiple objects returned by get_or_create", err.args[0])
                        has_errors = True
                    except (ValidationError, ValueError) as err:
                        run_detail.end_with_error("Invalid data", err.args[0])
                        has_errors = True
                    except Error as err:
                        run_detail.end_with_error("Database error while processing file", err)
                        has_errors = True

                    # Incrementing Run processed counter
                    self._parser_run.inc_processed()
            return not has_errors
        except Exception as err:
            if run_detail:
                run_detail.end_with_error('Critical Error', err)
            raise RuntimeParserError("Error while processing data", err)
