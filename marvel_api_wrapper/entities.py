import datetime
import json
import re
from typing import List

from dateutil.parser import parse

from marvel_api_wrapper.endpoint_fabric import EndpointFabric


class ActionNotSupportedError(Exception):
    pass


class MarvelAPIData:
    def __bool__(self):
        return True

    def to_dict(self):
        return {}


class MarvelAPIJSONEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, MarvelAPIData):
            return z.to_dict()
        elif isinstance(z, datetime.datetime):
            return z.isoformat()
        else:
            super().default(z)


class Url(MarvelAPIData):
    __slots__ = ['_url', '_type']

    # noinspection PyShadowingBuiltins
    def __init__(self, url: str, type: str):
        self._url = url
        self._type = type

    @property
    def url(self) -> str:
        return self._url

    @property
    def type(self) -> str:
        return self._type

    def __str__(self) -> str:
        return "[URL] type: {0._type}; url: {0._url}".format(self)

    def to_dict(self):
        return {
            'url': self._url,
            'type': self._type
        }


class Text(MarvelAPIData):
    __slots__ = ['_type', '_language', '_text']

    # noinspection PyShadowingBuiltins
    def __init__(self, type: str, language: str, text: str):
        self._text: str = text
        self._language = language
        self._type = type

    @property
    def text(self) -> str:
        return self._text

    @property
    def type(self) -> str:
        return self._type

    @property
    def language(self) -> str:
        return self._language

    def __str__(self) -> str:
        return "[Text] type: {0._type}; language: {0._language}; text: {0._text}".format(self)

    def to_dict(self):
        return {
            'text': self._text,
            'language': self._language,
            'type': self._type
        }


class Image(MarvelAPIData):
    __slots__ = ['_path', '_extension']

    def __init__(self, path: str, extension: str):
        self._path = path
        self._extension = extension

    @property
    def path(self) -> str:
        return self._path

    @property
    def extension(self) -> str:
        return self._extension

    def get_link(self, size: str = None):
        if size:
            size = '/' + size
        return "{0}{1}.{2}".format(self._path, size, self.extension)

    def __str__(self):
        return "[Image] path: {0._path}; extension: {0._extension}".format(self)

    def to_dict(self):
        return {
            'path': self._path,
            'extension': self._extension
        }


class ComicsDate(MarvelAPIData):
    __slots__ = ['_type', '_date']

    # noinspection PyShadowingBuiltins
    def __init__(self, date: datetime.datetime, type: str):
        self._date = date
        self._type = type

    @property
    def type(self) -> str:
        return self._type

    @property
    def date(self) -> datetime.datetime:
        return self._date

    def __str__(self):
        return "[ComicsDate] type: {0._type}; date: {0._date}".format(self)

    def to_dict(self):
        return {
            'type': self._type,
            'date': self._date
        }


class ComicsPrice(MarvelAPIData):
    __slots__ = ['_type', '_price']

    # noinspection PyShadowingBuiltins
    def __init__(self, price: float, type: str):
        self._price = price
        self._type = type

    @property
    def type(self) -> str:
        return self._type

    @property
    def price(self) -> float:
        return self._price

    def __str__(self):
        return "[ComicsPrice] type: {0._type}; date: {0._price}".format(self)

    def to_dict(self):
        return {
            'type': self._type,
            'date': self._price
        }


class ResourceList(MarvelAPIData):
    __slots__ = ['_available', '_collection_uri', '_entities', '_entities_endpoint']

    # noinspection PyPep8Naming
    def __init__(self, endpoint_class, available, collectionURI, **kwargs):
        self._collection_uri = collectionURI
        self._available = available
        f = EndpointFabric.get_instance()
        self._entities_endpoint = f.get_endpoint(endpoint_class, endpoint_url=self._collection_uri)
        if available == 0:
            self._entities = []
        else:
            self._entities = None

    def to_dict(self):
        return {
            'available': self._available,
            'collectionURI': self._collection_uri
        }

    @property
    def entities(self):
        if self._entities is None:
            self._entities = self._entities_endpoint.get_all()
        return self._entities

    @property
    def collection_uri(self):
        return self._collection_uri

    @property
    def available(self):
        return self._available


class NotSupportedResourceList(MarvelAPIData):

    def __bool__(self):
        return False

    @property
    def entities(self):
        raise ActionNotSupportedError

    @property
    def collection_uri(self):
        raise ActionNotSupportedError

    @property
    def available(self):
        raise ActionNotSupportedError


# Summary Entities


class BaseSummary(MarvelAPIData):
    __slots__ = ['_name', '_resource_uri', '_id', '_entity', '_entity_endpoint']

    # noinspection PyPep8Naming
    def __init__(self, name, resourceURI, **kwargs):
        self._name = name
        self._resource_uri = resourceURI
        self._id = int(re.search(r"\d+$", resourceURI)[0])
        self._entity = None
        f = EndpointFabric.get_instance()
        self._entity_endpoint = f.get_endpoint(self.get_endpoint_class(), endpoint_url=self._resource_uri)

    def to_dict(self):
        return {
            'name': self._name,
            'resourceURI': self._resource_uri
        }

    @staticmethod
    def get_endpoint_class():
        from marvel_api_wrapper.endpoints import SingleEndpoint
        return SingleEndpoint

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def resource_uri(self) -> str:
        return self._resource_uri

    @property
    def entity(self):
        if not self._entity:
            self._entity = self._entity_endpoint.get()
        return self._entity

    def __str__(self):
        return "[{0.__class__}] {0.name}".format(self)


class SeriesSummary(BaseSummary):
    @staticmethod
    def get_endpoint_class():
        from marvel_api_wrapper.endpoints import SeriesDetailEndpoint
        return SeriesDetailEndpoint


class ComicSummary(BaseSummary):
    @staticmethod
    def get_endpoint_class():
        from marvel_api_wrapper.endpoints import ComicDetailEndpoint
        return ComicDetailEndpoint


class EventSummary(BaseSummary):
    @staticmethod
    def get_endpoint_class():
        from marvel_api_wrapper.endpoints import EventDetailEndpoint
        return EventDetailEndpoint

# Full Entities


class BaseEntity(MarvelAPIData):
    __slots__ = ['_id', '_modified', '_resource_uri', '_urls', '_thumbnail', '_comics', '_events', '_series',
                 '_creators', '_characters']

    # noinspection PyPep8Naming
    def __init__(self, id: int, resourceURI: str, modified: datetime.datetime = None, urls: List[Url] = None,
                 thumbnail: Image = None, **kwargs):
        self._id = id
        self._modified = modified
        self._resource_uri = resourceURI
        self._urls = urls
        self._thumbnail = thumbnail

        from marvel_api_wrapper import endpoints

        comics = kwargs.get('comics')
        if comics:
            self._comics = ResourceList(endpoints.ComicsListEndpoint, **comics)
        else:
            self._comics = NotSupportedResourceList()

        events = kwargs.get('events')
        if events:
            self._events = ResourceList(endpoints.EventsListEndpoint, **events)
        else:
            self._events = NotSupportedResourceList()

        series = kwargs.get('series')
        if series:
            self._series = ResourceList(endpoints.SeriesListEndpoint, **series)
        else:
            self._series = NotSupportedResourceList()

        creators = kwargs.get('creators')
        if creators:
            self._creators = ResourceList(endpoints.CreatorsListEndpoint, **creators)
        else:
            self._creators = NotSupportedResourceList()

        characters = kwargs.get('characters')
        if characters:
            self._characters = ResourceList(endpoints.CharactersListEndpoint, **characters)
        else:
            self._characters = NotSupportedResourceList()

    def to_dict(self):
        d = {
            'id': self._id,
            'resourceURI': self._resource_uri,
            'modified': self._modified,
            'urls': [x.to_dict() for x in self._urls],
            'thumbnail': self._thumbnail.to_dict()
        }

        if self._comics:
            d['comics'] = self._comics.to_dict()
        if self._events:
            d['events'] = self._events.to_dict()
        if self._series:
            d['series'] = self._series.to_dict()
        if self._creators:
            d['creators'] = self._creators.to_dict()
        if self._characters:
            d['characters'] = self._characters.to_dict()

        return d

    @classmethod
    def convert_dict(cls, d):
        res = d
        modified = d.get('modified')
        if modified:
            res['modified'] = parse(modified)

        thumbnail = d.get('thumbnail')
        if thumbnail:
            res['thumbnail'] = Image(**thumbnail)

        urls = d.get('urls')
        if urls:
            res['urls'] = [Url(**x) for x in urls]

        return res

    @classmethod
    def create_from_dict(cls, d):
        params = cls.convert_dict(d)
        return cls(**params)

    @property
    def id(self) -> int:
        return self._id

    @property
    def modified(self) -> datetime.datetime:
        return self._modified

    @property
    def resource_uri(self) -> str:
        return self._resource_uri

    @property
    def urls(self) -> List[Url]:
        return self._urls

    @property
    def thumbnail(self) -> Image:
        return self._thumbnail

    @property
    def comics(self):
        return self._comics

    @property
    def events(self):
        return self._events

    @property
    def series(self):
        return self._series

    @property
    def creators(self):
        return self._creators

    @property
    def characters(self):
        return self._characters


class Comic(BaseEntity):
    __slots__ = ['_digital_id', '_title', '_issue_number', '_variant_descriptor', '_description', '_isbn', '_upc',
                 '_diamond_code', '_ean', '_issn', '_format', '_page_count', '_text_objects', '_series', '_variants',
                 '_collections', '_collected_issues', '_dates', '_prices', '_images']

    # noinspection PyPep8Naming,PyShadowingBuiltins
    def __init__(self,
                 id: int,
                 resourceURI: str,
                 modified: datetime.datetime = None,
                 urls: List[Url] = None,
                 thumbnail: Image = None,

                 digitalId: int = None,
                 title: str = None,
                 issueNumber: int = None,
                 variantDescriptor: str = None,
                 description: str = None,
                 isbn: str = None,
                 upc: str = None,
                 diamondCode: str = None,
                 ean: str = None,
                 issn: str = None,
                 format: str = None,
                 pageCount: int = None,
                 textObjects: List[Text] = None,
                 series: SeriesSummary = None,
                 variants: List[ComicSummary] = None,
                 collections: List[ComicSummary] = None,
                 collectedIssues: List[ComicSummary] = None,
                 dates: List[ComicsDate] = None,
                 prices: List[ComicsPrice] = None,
                 images: List[Image] = None,
                 **kwargs):
        super(Comic, self).__init__(id, resourceURI, modified, urls, thumbnail, **kwargs)
        self._digital_id = digitalId
        self._title = title
        self._issue_number = issueNumber
        self._variant_descriptor = variantDescriptor
        self._description = description
        self._isbn = isbn
        self._upc = upc
        self._diamond_code = diamondCode
        self._ean = ean
        self._issn = issn
        self._format = format
        self._page_count = pageCount
        self._text_objects = textObjects
        self._series = series
        self._variants = variants
        self._collections = collections
        self._collected_issues = collectedIssues
        self._dates = dates
        self._prices = prices
        self._images = images

    def to_dict(self):
        super_d = super(Comic, self).to_dict()
        d = {
            'digitalId': self._digital_id,
            'title': self._title,
            'issueNumber': self._issue_number,
            'variantDescriptor': self._variant_descriptor,
            'description': self._description,
            'isbn': self._isbn,
            'upc': self._upc,
            'diamondCode': self._diamond_code,
            'ean': self._ean,
            'issn': self._issn,
            'format': self._format,
            'pageCount': self._page_count,
            'textObjects': [x.to_dict for x in self._text_objects],
            'series': self._series.to_dict(),
            'variants': [x.to_dict() for x in self._variants],
            'collections': [x.to_dict() for x in self._collections],
            'collectedIssues': [x.to_dict() for x in self._collected_issues],
            'dates': [x.to_dict() for x in self._dates],
            'prices': [x.to_dict() for x in self._prices],
            'images': [x.to_dict() for x in self._images],
        }

        super_d.update(d)
        return super_d

    @classmethod
    def convert_dict(cls, d):
        res = super().convert_dict(d)

        text_objects = d.get('textObjects')
        if text_objects:
            res['textObjects'] = [Text(**x) for x in text_objects]

        series = d.get('series')
        if series:
            res['series'] = SeriesSummary(**series)

        variants = d.get('variants')
        if variants:
            res['variants'] = [ComicSummary(**x) for x in variants]

        collections = d.get('collections')
        if variants:
            res['collections'] = [ComicSummary(**x) for x in collections]

        collected_issues = d.get('collectedIssues')
        if variants:
            res['collectedIssues'] = [ComicSummary(**x) for x in collected_issues]

        dates = d.get('dates')
        if dates:
            res['dates'] = [ComicsDate(parse(x['date']), x['type']) for x in dates]

        prices = d.get('prices')
        if prices:
            res['prices'] = [ComicsPrice(**x) for x in prices]

        images = d.get('images')
        if images:
            res['images'] = [Image(**x) for x in images]

        return res

    def __str__(self):
        return "[{0.__class__] id: {0._id}; title: {0._title}".format(self)

    @property
    def digital_id(self) -> int:
        return self._digital_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def issue_number(self) -> int:
        return self._issue_number

    @property
    def variant_descriptor(self) -> str:
        return self._variant_descriptor

    @property
    def description(self) -> str:
        return self._description

    @property
    def isbn(self) -> str:
        return self._isbn

    @property
    def upc(self) -> str:
        return self._upc

    @property
    def diamond_code(self) -> str:
        return self._diamond_code

    @property
    def ean(self) -> str:
        return self._ean

    @property
    def issn(self) -> str:
        return self._issn

    @property
    def format(self) -> str:
        return self._format

    @property
    def page_count(self) -> int:
        return self._page_count

    @property
    def text_objects(self) -> List[Text]:
        return self._text_objects

    @property
    def series(self) -> SeriesSummary:
        return self._series

    @property
    def variants(self) -> List[ComicSummary]:
        return self._variants

    @property
    def collections(self) -> List[ComicSummary]:
        return self._collections

    @property
    def collected_issues(self) -> List[ComicSummary]:
        return self._collected_issues

    @property
    def dates(self) -> List[ComicsDate]:
        return self._dates

    @property
    def images(self) -> List[Image]:
        return self._images

    @property
    def prices(self) -> List[ComicsPrice]:
        return self._prices


class Character(BaseEntity):
    __slots__ = ['_name', '_description']

    # noinspection PyPep8Naming
    def __init__(self,
                 id: int,
                 resourceURI: str,
                 modified: datetime.datetime = None,
                 urls: List[Url] = None,
                 thumbnail: Image = None,

                 name: str = None,
                 description: str = None,
                 **kwargs):
        super().__init__(id, resourceURI, modified, urls, thumbnail, **kwargs)
        self._name = name
        self._description = description

    def __str__(self):
        return "[{0.__class__] id: {0._id}; name: {0._name}".format(self)

    def to_dict(self):
        super_d = super(Character, self).to_dict()
        d = {
            'name': self._name,
            'description': self._description,
        }

        super_d.update(d)
        return super_d

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description


class Creator(BaseEntity):
    __slots__ = ['_first_name', '_middle_name', '_last_name', '_suffix', '_full_name']

    # noinspection PyPep8Naming
    def __init__(self,
                 id: int,
                 resourceURI: str,
                 modified: datetime.datetime = None,
                 urls: List[Url] = None,
                 thumbnail: Image = None,

                 firstName: str = None,
                 middleName: str = None,
                 lastName: str = None,
                 suffix: str = None,
                 fullName: str = None,
                 **kwargs):
        super().__init__(id, resourceURI, modified, urls, thumbnail, **kwargs)
        self._first_name = firstName
        self._middle_name = middleName
        self._last_name = lastName
        self._suffix = suffix
        self._full_name = fullName

    def __str__(self):
        return "[{0.__class__] id: {0._id}; full name: {0._full_name}".format(self)

    def to_dict(self):
        super_d = super(Creator, self).to_dict()
        d = {
            'firstName': self._first_name,
            'middleName': self._middle_name,
            'lastName': self._last_name,
            'suffix': self._suffix,
            'fullName': self._full_name
        }

        super_d.update(d)
        return super_d

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def middle_name(self) -> str:
        return self._middle_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def suffix(self) -> str:
        return self._suffix

    @property
    def full_name(self) -> str:
        return self._full_name


class Event(BaseEntity):
    __slots__ = ['_title', '_description', '_start', '_end', '_next', '_previous']

    # noinspection PyPep8Naming,PyShadowingBuiltins
    def __init__(self,
                 id: int,
                 resourceURI: str,
                 modified: datetime.datetime = None,
                 urls: List[Url] = None,
                 thumbnail: Image = None,

                 title: str = None,
                 description: str = None,
                 start: datetime.datetime = None,
                 end: datetime.datetime = None,
                 next: EventSummary = None,
                 previous: EventSummary = None,
                 **kwargs):
        super().__init__(id, resourceURI, modified, urls, thumbnail, **kwargs)
        self._title = title
        self._description = description
        self._start = start
        self._end = end
        self._next = next
        self._previous = previous

    def __str__(self):
        return "[{0.__class__] id: {0._id}; title: {0._title}".format(self)

    def to_dict(self):
        super_d = super(Event, self).to_dict()
        d = {
            'title': self._title,
            'description': self._description,
            'start': self._start,
            'end': self._end,
            'next': self._next,
            'previous': self._previous
        }

        super_d.update(d)
        return super_d

    @classmethod
    def convert_dict(cls, d):
        res = super().convert_dict(d)

        start = d.get('start')
        if start:
            res['start'] = parse(start)

        end = d.get('end')
        if end:
            res['end'] = parse(end)

        next = d.get('next')
        if next:
            res['next'] = EventSummary(**next)

        previous = d.get('previous')
        if next:
            res['previous'] = EventSummary(**previous)

        return res

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def next(self):
        return self._next

    @property
    def previous(self):
        return self._previous


class Series(BaseEntity):
    __slots__ = ['_title', '_description', '_start_year', '_end_year', '_rating', '_next', '_previous']

    # noinspection PyPep8Naming,PyShadowingBuiltins
    def __init__(self,
                 id: int,
                 resourceURI: str,
                 modified: datetime.datetime = None,
                 urls: List[Url] = None,
                 thumbnail: Image = None,

                 title: str = None,
                 description: str = None,
                 startYear: int = None,
                 endYear: int = None,
                 rating: str = None,
                 next: EventSummary = None,
                 previous: EventSummary = None,
                 **kwargs):
        super().__init__(id, resourceURI, modified, urls, thumbnail, **kwargs)
        self._rating = rating
        self._title = title
        self._description = description
        self._start_year = startYear
        self._end_year = endYear
        self._next = next
        self._previous = previous

    def __str__(self):
        return "[{0.__class__] id: {0._id}; title: {0._title}".format(self)

    def to_dict(self):
        super_d = super(Series, self).to_dict()
        d = {
            'rating': self._title,
            'title': self._title,
            'description': self._description,
            'startYear': self._start_year,
            'endYear': self._end_year,
            'next': self._next,
            'previous': self._previous
        }

        super_d.update(d)
        return super_d

    @classmethod
    def convert_dict(cls, d):
        res = super().convert_dict(d)

        next = d.get('next')
        if next:
            res['next'] = SeriesSummary(**next)

        previous = d.get('previous')
        if previous:
            res['previous'] = SeriesSummary(**previous)

        return res

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def start_year(self):
        return self._start_year

    @property
    def end_year(self):
        return self._end_year

    @property
    def rating(self):
        return self._rating

    @property
    def next(self):
        return self._next

    @property
    def previous(self):
        return self._previous
