"""
Different parsers for getting comics info
"""
import datetime
import inspect
import re
import tempfile

import boto3
import botocore
import botocore.exceptions
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db import Error
from django.utils import timezone

from comics_db import models as comics_models
from comics_db.models import ParserRun, ParserRunDetail, CloudFilesParserRunDetail
from comics_db.reader import ComicsReader
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

    For saving run parameters in log^ put them in _params dictionary
    """
    PARSER_CODE = "BASE"  # Parser code for linking log to specific parser type
    RUN_DETAIL_MODEL = ParserRunDetail  # Model for saving parser detail logs

    def __init__(self):
        self._parser_run = None
        self._data = None
        self._params = {}

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

    def _postprocessing(self):
        """
        Executing podt processing operations. Should be overridden in specific parser classes

        If critical error happens during processing, method should raise RuntimeParserError.
        Critical error - error which prevent parser from continue work.
        :return: None
        """

    def run(self, celery_task_id=None):
        """
        Main method for running parser.

        Handles creating record in parser run log, checks correctness of specific implementation and handles
        unrecoverable errors.
        :return: Run result boolean (True - success, False - error)
        """
        try:
            # Initializing Run
            self._parser_run = ParserRun()
            self._parser_run.celery_task_id = celery_task_id

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
            for k, v in self._params.items():
                run_param = comics_models.ParserRunParams(parser_run=self._parser_run, name=k, val=str(v))
                run_param.save()

            # Starting processing
            process_result = self._process()

            # Setting result status and ending work
            if process_result:
                self._parser_run.status = "SUCCESS"
            else:
                self._parser_run.status = "ENDED_WITH_ERRORS"

            self._postprocessing()

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

    def __init__(self, path_prefix, full=False, load_covers=False):
        super().__init__()
        self._params['path_prefix'] = path_prefix
        self._params['full'] = full
        self._params['load_covers'] = load_covers
        self._publishers = set()
        self._universes = set()
        self._titles = set()
        self._issues = set()

        # Initialize bucket connection
        session = boto3.session.Session()
        s3 = session.resource('s3', region_name=settings.DO_REGION_NAME,
                              endpoint_url=settings.DO_ENDPOINT_URL,
                              aws_access_key_id=settings.DO_KEY_ID,
                              aws_secret_access_key=settings.DO_SECRET_ACCESS_KEY)
        self._bucket = s3.Bucket(settings.DO_STORAGE_BUCKET_NAME)

    def _prepare(self):
        try:
            bucket_comics = self._bucket.objects.filter(Prefix=self._params['path_prefix'])
            self._data = [x.key for x in bucket_comics if self._FILE_REGEX.search(x.key)]
        except botocore.exceptions.ConnectionError:
            raise RuntimeParserError("Could not establish connection to DO cloud")
        except botocore.exceptions.ClientError as err:
            raise RuntimeParserError("boto3 client error while preparing data", err.msg)
        except Exception as err:
            raise RuntimeParserError("Error while preparing data", err.args[0])

    @property
    def _items_count(self):
        if self._data:
            return len(self._data)
        else:
            return 0

    def _process(self):
        run_detail = None

        # Dicts for already parsed parent entities
        publishers = {}
        universes = {}
        title_types = {}
        titles = {}
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
                        publisher = publishers.get(info['publisher'], None)  # Trying to get already parsed version
                        if not publisher:  # Not parsed, looking in DB
                            publisher, created = comics_models.Publisher.objects.get_or_create(name=info['publisher'])
                            if created:  # Not found in DB, creating
                                publisher.save()
                            publishers[info['publisher']] = publisher  # Saving in parsed dict
                        if self._params['full']:  # Saving in set for not deleting
                            self._publishers.add(publisher.id)

                        # Getting or creating Universe
                        universe = universes.get((info['universe'], publisher.id),
                                                 None)  # Trying to get already parsed version
                        if not universe:  # Not parsed, looking in DB
                            universe, created = comics_models.Universe.objects.get_or_create(name=info['universe'],
                                                                                             publisher=publisher)
                            if created:  # Not found in DB, creating
                                universe.save()
                            universes[(info['universe'], publisher.id)] = universe  # Saving in parsed dict
                        if self._params['full']:  # Saving in set for not deleting
                            self._universes.add(universe.id)

                        # Getting or creating Title type
                        title_type = title_types.get(info['title_type'])  # Trying to get already parsed version
                        if not title_type:  # Not parsed, looking in DB
                            title_type, created = comics_models.TitleType.objects.get_or_create(name=info['title_type'])
                            if created:  # Not found in DB, creating
                                title_type.save()
                            title_types[info['title_type']] = title_type  # Saving in parsed dict

                        # Getting or creating Title
                        title = titles.get(((info['title'] or info['issue_name']),
                                            publisher.id,
                                            universe.id,
                                            title_type.id), None)  # Trying to get already parsed version
                        if not title:  # Not parsed, looking in DB
                            title, created = comics_models.Title.objects.get_or_create(path_key=(info['title']
                                                                                                 or info['issue_name']),
                                                                                       publisher=publisher,
                                                                                       universe=universe,
                                                                                       title_type=title_type,
                                                                                       defaults={
                                                                                           'name': (info['title']
                                                                                                    or info[
                                                                                                        'issue_name'])
                                                                                       })
                            if created:  # Not found in DB, creating
                                title.save()

                            titles[((info['title'] or info['issue_name']),  # Saving in parsed dict
                                    publisher.id,
                                    universe.id,
                                    title_type.id)] = title
                        if self._params['full']:  # Saving in set for not deleting
                            self._titles.add(title.id)

                        # Getting publish date
                        publish_date = datetime.date(int(info['year']), 1, 1)

                        # Getting number
                        try:
                            number = int(info['number'])
                        except ValueError:
                            number = 0
                        except TypeError:
                            number = None

                        # Getting or creating issue
                        issue, created = comics_models.Issue.objects.get_or_create(link=file_key,
                                                                                   defaults={
                                                                                       'name': info['issue_name'],
                                                                                       'number': number,
                                                                                       'title': title,
                                                                                       'publish_date': publish_date
                                                                                   })
                        if created:
                            issue.save()

                        if self._params['full']:  # Saving in set for not deleting
                            self._issues.add(issue.id)

                        run_detail.issue = issue
                        run_detail.created = created
                        if self._params['load_covers'] and not issue.main_cover:
                            try:
                                with tempfile.NamedTemporaryFile() as comics_file:
                                    self._bucket.download_fileobj(file_key, comics_file)
                                    with ComicsReader(comics_file) as reader:
                                        with reader.get_page_file(0) as cover:
                                            issue.main_cover.save(cover.name, cover)
                                            issue.save()
                                run_detail.end_with_success()
                            except Error as err:
                                run_detail.end_with_error("Could not get issue cover", err.args[0])
                        else:
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
            return not has_errors
        except Exception as err:
            if run_detail:
                run_detail.end_with_error('Critical Error', err)
            raise RuntimeParserError("Error while processing data", err.args[0])

    def _postprocessing(self):
        """
        Delete elements which does not have corresponding file key
        :return:
        """
        try:
            if self._params['full']:
                comics_models.Issue.objects.exclude(id__in=self._issues).delete()
                comics_models.Title.objects.exclude(id__in=self._titles).delete()
                comics_models.Universe.objects.exclude(id__in=self._universes).delete()
                comics_models.Publisher.objects.exclude(id__in=self._publishers).delete()
        except Error as err:
            raise RuntimeParserError("Error while performing postprocessing", err.args[0])
