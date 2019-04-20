"""
Different parsers for getting comics info
"""
import datetime
import inspect
import json
import re
import tempfile
from typing import NoReturn

import boto3
import botocore
import botocore.exceptions
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db import Error
from django.db.models import Count, Max
from django.template.loader import render_to_string
from django.utils import timezone
from requests import HTTPError, RequestException

from comics_db import models as comics_models
from comics_db.models import ParserRun, ParserRunDetail, CloudFilesParserRunDetail, MarvelAPIParserRunDetail, \
    MarvelAPIComics, MarvelAPICharacter, MarvelAPICreator, MarvelAPIEvent, MarvelAPISeries, MarvelAPIImage, \
    MarvelAPISiteUrl
from comics_db.reader import ComicsReader
from comicsdb import settings
from marvel_api_wrapper import endpoints, entities
from marvel_api_wrapper.endpoint_fabric import EndpointFabric
from marvel_api_wrapper.endpoints import CreatorsListEndpoint, ComicsListEndpoint, CharactersListEndpoint, \
    EventsListEndpoint, SeriesListEndpoint, APIRateLimitError, APIError
from marvel_api_wrapper.entities import MarvelAPIJSONEncoder


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
    PARSER_NAME = 'Base parser'
    RUN_DETAIL_MODEL = ParserRunDetail  # Model for saving parser detail logs

    def __init__(self):
        self._parser_run = None
        self._data = None
        self._params = {}

    @property
    def _items_count(self) -> int:
        """
        Count items to be processed by parser. Should be overridden in specific parser classes
        :return: items count
        """
        return 0

    def _prepare(self) -> NoReturn:
        """
        Prepare data. Should be overridden in specific parser classes

        Preparing data i.e. retrieve data that will be parsed from server or select object for parse from DB
        :return: None
        """

    def _process(self) -> bool:
        """
        Method for parser work. Should be overridden in specific parser classes

        If critical error happens during processing, method should raise RuntimeParserError.
        Critical error - error which prevent parser from continue work.
        Errors which happens during processing one isolated item are not critical and should be handled within method
        (e.g. marked as error in log)

        :return: Run result boolean (True - success, False - ended with errors)
        """
        return True

    def _postprocessing(self) -> NoReturn:
        """
        Executing podt processing operations. Should be overridden in specific parser classes

        If critical error happens during processing, method should raise RuntimeParserError.
        Critical error - error which prevent parser from continue work.
        :return: None
        """

    @staticmethod
    def _notify_staff(message_html, message_txt, subject):
        for user in User.objects.filter(is_staff=True):
            msg = EmailMultiAlternatives(subject=subject,
                                         from_email="noreply@comicsdb.nonameitem.com",
                                         to=[user.email],
                                         body=message_txt)
            msg.attach_alternative(message_html, "text/html")
            msg.send()

    def _notify_staff_start(self):
        data = {
            'parser_name': self.PARSER_NAME,
            'parameters': self._params.items(),
            'run_link': settings.BASE_URL + self._parser_run.page,
            'start_time': self._parser_run.start
        }

        subject = "[ComicsDB] %s started" % self.PARSER_NAME
        message_txt = render_to_string("comics_db/admin/notifications/parser_started.txt", data)
        message_html = render_to_string("comics_db/admin/notifications/parser_started.html", data)
        self._notify_staff(message_html, message_txt, subject)

    def _notify_staff_success(self):
        data = {
            'parser_name': self.PARSER_NAME,
            'parameters': self._params.items(),
            'run_link': settings.BASE_URL + self._parser_run.page,
            'start_time': self._parser_run.start,
            'end_time': self._parser_run.end,
            'status': self._parser_run.get_status_display(),
            'record_total': self._parser_run.items_count,
            'record_processed': self._parser_run.processed,
            'record_success': self._parser_run.success_count,
            'record_error': self._parser_run.error_count
        }
        subject = "[ComicsDB] %s ended" % self.PARSER_NAME
        message_txt = render_to_string("comics_db/admin/notifications/parser_ended.txt", data)
        message_html = render_to_string("comics_db/admin/notifications/parser_ended.html", data)
        self._notify_staff(message_html, message_txt, subject)

    def _notify_staff_error(self):
        data = {
            'parser_name': self.PARSER_NAME,
            'parameters': self._params.items(),
            'run_link': settings.BASE_URL + self._parser_run.page,
            'start_time': self._parser_run.start,
            'end_time': self._parser_run.end,
            'status': self._parser_run.get_status_display(),
            'record_total': self._parser_run.items_count,
            'record_processed': self._parser_run.processed,
            'record_success': self._parser_run.success_count,
            'record_error': self._parser_run.error_count,
            'error': self._parser_run.error,
            'error_detail': self._parser_run.error_detail

        }
        subject = "[ComicsDB] %s ended with critical error" % self.PARSER_NAME
        message_txt = render_to_string("comics_db/admin/notifications/parser_error.txt", data)
        message_html = render_to_string("comics_db/admin/notifications/parser_error.html", data)
        self._notify_staff(message_html, message_txt, subject)

    def run(self, celery_task_id: int = None) -> bool:
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
            self._parser_run.save()

            for k, v in self._params.items():
                run_param = comics_models.ParserRunParams(parser_run=self._parser_run, name=k, val=str(v))
                run_param.save()
            self._notify_staff_start()

            # Preparing data, filling items count and saving Run log record to table
            self._parser_run.status = 'COLLECTING'
            self._parser_run.save()
            self._prepare()
            self._parser_run.items_count = self._items_count
            self._parser_run.status = 'RUNNING'
            self._parser_run.save()

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
            self._notify_staff_success()
            return True

        except ParserError as err:
            self._parser_run.status = err.STATUS_CODE
            self._parser_run.error = err.message
            self._parser_run.error_detail = err.detail
            self._parser_run.end = timezone.now()
            self._parser_run.save()
            self._notify_staff_error()
            return False
        except Exception as err:
            self._parser_run.status = "INVALID_PARSER"
            self._parser_run.error = "{0} Unhandled error in method run".format(BaseParser)
            self._parser_run.error_detail = err
            self._parser_run.end = timezone.now()
            self._parser_run.save()
            self._notify_staff_error()
            return False


class CloudFilesParser(BaseParser):
    PARSER_CODE = "CLOUD_FILES"
    PARSER_NAME = "Cloud files parser"
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
                    run_detail.groups = json.dumps(info, indent=2)
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
                                                                                       defaults={
                                                                                           'name': (info['title']
                                                                                                    or info[
                                                                                                        'issue_name']),
                                                                                           'title_type': title_type
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
                            except Exception as err:
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
        Postprocessing task:
            * Delete empty titles, universes and publishers
            * Clean up at full reload
            * Set title covers as first issue cover
        :return:
        """
        try:
            comics_models.Title.objects.annotate(issue_count=Count('issues', distinct=True)) \
                .filter(issue_count=0).delete()
            comics_models.Universe.objects.annotate(title_count=Count('titles', distinct=True)) \
                .filter(title_count=0).delete()
            comics_models.Publisher.objects.annotate(title_count=Count('titles', distinct=True)) \
                .annotate(universe_count=Count('universes', distinct=True)).filter(title_count=0, universe_count=0) \
                .delete()
            if self._params['full']:
                comics_models.Issue.objects.exclude(id__in=self._issues).delete()
                comics_models.Title.objects.exclude(id__in=self._titles).delete()
                comics_models.Universe.objects.exclude(id__in=self._universes).delete()
                comics_models.Publisher.objects.exclude(id__in=self._publishers).delete()
            if self._params['load_covers']:
                for t in comics_models.Title.objects.filter(image=''):
                    i = t.issues.exclude(main_cover='').order_by('number').first()
                    if i:
                        t.image.save(i.main_cover.name, i.main_cover.file)
                        t.save()
        except Error as err:
            raise RuntimeParserError("Error while performing postprocessing", err.args[0])


class MarvelAPIParser(BaseParser):
    PARSER_CODE = "MARVEL_API"
    PARSER_NAME = "Marvel API parser"
    RUN_DETAIL_MODEL = MarvelAPIParserRunDetail

    MODELS = {
        "COMICS": MarvelAPIComics,
        "CHARACTER": MarvelAPICharacter,
        "CREATOR": MarvelAPICreator,
        "EVENT": MarvelAPIEvent,
        "SERIES": MarvelAPISeries
    }

    def __init__(self, incremental=False):
        super().__init__()
        self._params['incremental'] = incremental
        f = EndpointFabric.get_instance(public_key=settings.MARVEL_PUBLIC_KEY, private_key=settings.MARVEL_PRIVATE_KEY)
        self._creators_endpoint = f.get_endpoint(CreatorsListEndpoint)
        self._comics_endpoint = f.get_endpoint(ComicsListEndpoint)
        self._characters_endpoint = f.get_endpoint(CharactersListEndpoint)
        self._events_endpoint = f.get_endpoint(EventsListEndpoint)
        self._series_endpoint = f.get_endpoint(SeriesListEndpoint)

        self._creators = list()
        self._comics = list()
        self._characters = list()
        self._events = list()
        self._series = list()
        self._data = list()

        self._creators_dict = {}
        self._comics_dict = {}
        self._characters_dict = {}
        self._events_dict = {}
        self._series_dict = {}

    def _dump_api(self, entity_type, endpoint, target, **filters):
        if self._params['incremental']:
            target_model = self.MODELS[entity_type]
            max_modified = target_model.objects.aggregate(max_modified=Max('modified'))['max_modified']
            filters['modifiedSince'] = max_modified.date().isoformat()
        offset = 0
        # count = 0
        total = None
        detail = None

        while total is None or offset < total:
            try:
                filters['offset'] = offset
                filters['limit'] = 100
                detail = self.RUN_DETAIL_MODEL(action='GET', entity_type=entity_type, parser_run=self._parser_run,
                                               data=json.dumps(filters, indent=2))
                detail.save()
                data = endpoint.get(**filters)
                detail.end_with_success()
                if data['count'] == 0:
                    break
                target += data['results']
                # count += data['count']
                total = data['total']
                offset += data['count']
                # print(entity_type, total, count)
            except APIRateLimitError:
                if detail:
                    detail.end_with_error('API rate limit exceeded')
                raise RuntimeParserError('API rate limit exceeded')
            except APIError as err:
                if detail:
                    detail.end_with_error('API error', err.args[0])
                # raise RuntimeParserError(err.args[0])
            except RequestException as err:
                if detail:
                    detail.end_with_error('API error', err.args[0])
                # raise RuntimeParserError(err.args[0])

    def _prepare(self) -> NoReturn:
        self._dump_api('COMICS', self._comics_endpoint, self._comics, formatType='comic', noVariants='true',
                       orderBy='modified')
        self._dump_api('CHARACTER', self._characters_endpoint, self._characters, orderBy='modified')
        self._dump_api('CREATOR', self._creators_endpoint, self._creators, orderBy='modified')
        self._dump_api('EVENT', self._events_endpoint, self._events, orderBy='modified')
        self._dump_api('SERIES', self._series_endpoint, self._series, orderBy='modified')

        self._data = [('CREATOR', x) for x in self._creators]
        self._data += [('CHARACTER', x) for x in self._characters]
        self._data += [('EVENT', x) for x in self._events]
        self._data += [('SERIES', x) for x in self._series]
        self._data += [('COMICS', x) for x in self._comics]

    @property
    def _items_count(self) -> int:
        return len(self._data)

    def _process_comics(self, data: entities.Comic):
        # Series
        series = self._series_dict[data.series.id] or MarvelAPISeries.objects.get(id=data.series.id)

        comics, _ = MarvelAPIComics.objects.get_or_create(id=data.id, defaults={'series': series})
        comics.title = data.title
        comics.issue_number = data.issue_number
        comics.description = data.description
        comics.modified = data.modified
        comics.page_count = data.page_count
        comics.resource_URI = data.resource_uri

        # Thumbnail
        thumbnail, _ = MarvelAPIImage.objects.get_or_create(path=data.thumbnail.path,
                                                            extension=data.thumbnail.extension, comics=comics)
        thumbnail.save()

        # Urls
        for url in data.urls:
            u, _ = MarvelAPISiteUrl.objects.get_or_create(type=url.type, url=url.url, comics=comics)
            u.save()

        # Events
        if data.events.available == len(data.events.items):
            for event in data.events.items:
                event_record = self._events_dict.get(event.id) or \
                               MarvelAPIEvent.objects.get(id=event.id)
                comics.events.add(event_record)
        else:
            for event in data.events.entities:
                event_record = self._events_dict.get(event.id) or \
                               MarvelAPIEvent.objects.get(id=event.id)
                comics.events.add(event_record)

        # Characters
        if data.characters.available == len(data.characters.items):
            for character in data.characters.items:
                character_record = self._characters_dict.get(character.id) or \
                                   MarvelAPICharacter.objects.get(id=character.id)
                comics.characters.add(character_record)
        else:
            for character in data.characters.entities:
                character_record = self._characters_dict.get(character.id) or \
                                   MarvelAPICharacter.objects.get(id=character.id)
                comics.characters.add(character_record)

        # Creators
        if data.creators.available == len(data.creators.items):
            for creator in data.creators.items:
                creator_record = self._creators_dict.get(creator.id) or \
                                 MarvelAPICreator.objects.get(id=creator.id)
                comics.creators.add(creator_record, through_defaults={'role': creator.role})
        else:
            for creator in data.creators.entities:
                creator_record = self._creators_dict.get(creator.id) or \
                                 MarvelAPICreator.objects.get(id=creator.id)
                comics.creators.add(creator_record, through_defaults={'role': creator.role})

    def _process_creator(self, data: entities.Creator):
        creator, created = MarvelAPICreator.objects.get_or_create(id=data.id)
        creator.first_name = data.first_name
        creator.middle_name = data.middle_name
        creator.last_name = data.last_name
        creator.suffix = data.suffix
        creator.full_name = data.full_name
        creator.modified = data.modified
        creator.resource_URI = data.resource_uri
        creator.save()

        # Thumbnail
        thumbnail, _ = MarvelAPIImage.objects.get_or_create(path=data.thumbnail.path,
                                                            extension=data.thumbnail.extension, creator=creator)
        thumbnail.save()

        # Urls
        for url in data.urls:
            u, _ = MarvelAPISiteUrl.objects.get_or_create(type=url.type, url=url.url, creator=creator)
            u.save()

        self._creators_dict[data.id] = creator

    def _process_character(self, data: entities.Character):
        character, created = MarvelAPICharacter.objects.get_or_create(id=data.id)
        character.name = data.name
        character.description = data.description
        character.modified = data.modified
        character.resource_URI = data.resource_uri
        character.save()

        # Thumbnail
        thumbnail, _ = MarvelAPIImage.objects.get_or_create(path=data.thumbnail.path,
                                                            extension=data.thumbnail.extension, character=character)
        thumbnail.save()

        # Urls
        for url in data.urls:
            u, _ = MarvelAPISiteUrl.objects.get_or_create(type=url.type, url=url.url, character=character)
            u.save()

        self._characters_dict[data.id] = character

    def _process_event(self, data: entities.Event):
        event, _ = MarvelAPIEvent.objects.get_or_create(id=data.id)
        event.title = data.title
        event.description = data.description
        event.resource_URI = data.resource_uri
        event.modified = data.modified
        event.start = data.start
        event.end = data.end
        event.save()

        # Thumbnail
        thumbnail, _ = MarvelAPIImage.objects.get_or_create(path=data.thumbnail.path,
                                                            extension=data.thumbnail.extension, event=event)
        thumbnail.save()

        # Urls
        for url in data.urls:
            u, _ = MarvelAPISiteUrl.objects.get_or_create(type=url.type, url=url.url, event=event)
            u.save()

        self._events_dict[data.id] = event

    def _process_series(self, data: entities.Series):
        series, _ = MarvelAPISeries.objects.get_or_create(id=data.id)
        series.title = data.title
        series.description = data.description
        series.resource_URI = data.resource_uri
        series.start_year = data.start_year
        series.end_year = data.end_year
        series.rating = data.rating
        series.modified = data.modified
        series.save()

        # Thumbnail
        thumbnail, _ = MarvelAPIImage.objects.get_or_create(path=data.thumbnail.path,
                                                            extension=data.thumbnail.extension, series=series)
        thumbnail.save()

        # Urls
        for url in data.urls:
            u, _ = MarvelAPISiteUrl.objects.get_or_create(type=url.type, url=url.url, series=series)
            u.save()

        self._series_dict[data.id] = series

    def _process(self) -> bool:
        run_detail = None
        has_errors = False
        for i in self._data:
            try:
                run_detail = self.RUN_DETAIL_MODEL(action='PROCESS', entity_type=i[0], entity_id=i[1].id,
                                               data=json.dumps(i[1], indent=2, cls=MarvelAPIJSONEncoder),
                                               parser_run=self._parser_run)
                if i[0] == 'COMICS':
                    self._process_comics(i[1])
                elif i[0] == 'CHARACTER':
                    self._process_character(i[1])
                elif i[0] == 'CREATOR':
                    self._process_creator(i[1])
                elif i[0] == 'EVENT':
                    self._process_event(i[1])
                elif i[0] == 'SERIES':
                    self._process_series(i[1])
                run_detail.end_with_success()
            except MarvelAPISeries.DoesNotExist as err:
                if run_detail:
                    run_detail.end_with_error("Series does not exists", err.args[0])
                has_errors = True
            except MarvelAPIComics.DoesNotExist as err:
                if run_detail:
                    run_detail.end_with_error("Comics does not exists", err.args[0])
                has_errors = True
            except MarvelAPICharacter.DoesNotExist as err:
                if run_detail:
                    run_detail.end_with_error("Character does not exists", err.args[0])
                has_errors = True
            except MarvelAPIEvent.DoesNotExist as err:
                if run_detail:
                    run_detail.end_with_error("Event does not exists", err.args[0])
                has_errors = True
            except MarvelAPICreator.DoesNotExist as err:
                if run_detail:
                    run_detail.end_with_error("Creator does not exists", err.args[0])
                has_errors = True
            except MultipleObjectsReturned as err:
                if run_detail:
                    run_detail.end_with_error("Multiple objects returned by get_or_create", err.args[0])
                has_errors = True
            except (ValidationError, ValueError) as err:
                if run_detail:
                    run_detail.end_with_error("Invalid data", err.args[0])
                has_errors = True
            except Error as err:
                if run_detail:
                    run_detail.end_with_error("Database error while processing {0}".format(i[0].lower()), err)
                has_errors = True
        return not has_errors
