import datetime
import hashlib
from json import JSONDecodeError
from typing import Optional

import requests

import marvel_api_wrapper.entities # import BaseEntity, Creator, Comic, Character, Event, Series


class APIError(Exception):
    pass


class APIRateLimitError(Exception):
    pass


class BaseEndpoint:
    __slots__ = ['_public_key', '_private_key', 'endpoint_url']
    BASE_URL = "https://gateway.marvel.com/v1/public/"
    ENTITY_CODE = None
    ENTITY_CLASS = marvel_api_wrapper.entities.BaseEntity

    def __init__(self, **kwargs):
        self._public_key = kwargs.get('public_key')
        self._private_key = kwargs.get('private_key')
        self.endpoint_url = self._construct_endpoint_url(**kwargs)

    def _construct_endpoint_url(self, **kwargs) -> Optional[str]:
        return kwargs.get('endpoint_url')

    def _get_auth_params(self):
        ts = datetime.datetime.now().timestamp()
        m = hashlib.md5()
        m.update((str(ts) + self._private_key + self._public_key).encode())
        params = {'apikey': self._public_key, 'ts': ts, 'hash': m.hexdigest()}
        return params

    def get(self, retries=9, **filters) -> dict:
        params = filters
        params.update(self._get_auth_params())
        try:
            r = requests.get(self.endpoint_url, params=params, timeout=None)
            data = r.json()
            if r.status_code == 200:
                return self.convert_result(data)
            elif r.status_code == 401:
                raise APIError('Invalid credentials: %s' % data['message'])
            elif r.status_code == 409:
                raise APIError('Parameter error: %s' % data['status'])
            elif r.status_code == 429:
                raise APIRateLimitError
            else:
                if retries:
                    return self.get(retries - 1, **filters)
                else:
                    r.raise_for_status()
        except ConnectionError:
            if retries:
                return self.get(retries - 1, **filters)
            else:
                raise APIError('Could not establish connection to %s' % self.endpoint_url)
        except JSONDecodeError:
            raise APIError('Could not parse API response from %s' % self.endpoint_url)

    def get_all(self, **filters):
        results = []
        offset = 0
        count = 0
        total = None

        while not total or count < total:
            filters['offset'] = offset
            filters['limit'] = 100
            data = self.get(**filters)
            results += data['results']
            count += data['count']
            total = data['total']
            offset += 100

        return results

    def convert_result(self, data):
        data = data['data']
        objects = [self.ENTITY_CLASS.create_from_dict(x) for x in data['results']]
        data['results'] = objects
        return data


class MultipleEndpoint(BaseEndpoint):
    def _construct_endpoint_url(self, **kwargs) -> Optional[str]:
        if kwargs.get('endpoint_url'):
            return kwargs.get('endpoint_url')
        else:
            return self.BASE_URL + self.ENTITY_CODE


class SingleEndpoint(BaseEndpoint):
    def _construct_endpoint_url(self, **kwargs) -> Optional[str]:
        if kwargs.get('endpoint_url'):
            return kwargs.get('endpoint_url')
        else:
            endpoint_id = kwargs.get('id')
            if endpoint_id:
                return self.BASE_URL + self.ENTITY_CODE + '/' + str(endpoint_id)
            else:
                raise APIError('ID must be specified for Single Endpoint')

    def convert_result(self, data):
        data = data['data']
        obj = self.ENTITY_CLASS.create_from_dict(data['results'][0])
        return obj


class CreatorMixin:
    ENTITY_CODE = "creators"
    ENTITY_CLASS = marvel_api_wrapper.entities.Creator


class ComicsMixin:
    ENTITY_CODE = "comics"
    ENTITY_CLASS = marvel_api_wrapper.entities.Comic


class CharacterMixin:
    ENTITY_CODE = "character"
    ENTITY_CLASS = marvel_api_wrapper.entities.Character


class EventMixin:
    ENTITY_CODE = "events"
    ENTITY_CLASS = marvel_api_wrapper.entities.Event


class SeriesMixin:
    ENTITY_CODE = "series"
    ENTITY_CLASS = marvel_api_wrapper.entities.Series


class CreatorsListEndpoint(CreatorMixin, MultipleEndpoint):
    pass


class CreatorDetailEndpoint(CreatorMixin, SingleEndpoint):
    pass


class ComicsListEndpoint(ComicsMixin, MultipleEndpoint):
    pass


class ComicDetailEndpoint(ComicsMixin, SingleEndpoint):
    pass


class CharactersListEndpoint(CharacterMixin, MultipleEndpoint):
    pass


class CharacterDetailEndpoint(CharacterMixin, SingleEndpoint):
    pass


class EventsListEndpoint(EventMixin, MultipleEndpoint):
    pass


class EventDetailEndpoint(EventMixin, SingleEndpoint):
    pass


class SeriesListEndpoint(SeriesMixin, MultipleEndpoint):
    pass


class SeriesDetailEndpoint(SeriesMixin, SingleEndpoint):
    pass



