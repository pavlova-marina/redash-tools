import logging
import requests
import getpass
import json
import re
from requests import HTTPError

from redash_tools.core.entities import Query, Dashboard

logger = logging.getLogger(__name__)


class RedashSession:
   
    def __init__(self, url=None, api_key=None):
        """
        initializes RedashSession
        url is Redash's url, api_key is the user's API key
        """
        if url is None:
            url = input('Введите url (включая http/https): ').strip('/\\ ')
        if api_key is None:
            api_key = getpass.getpass(f'Введите API-ключ со страницы {url}/users/me : ')
        self.url = url
        self.s = requests.Session()
        self.s.headers.update({'Authorization': f'Key {api_key}',
                               'Content-Type': 'application/json'})

    def make_url(self, *args):
        args = list(args)
        args.insert(0, self.url)
        return '/'.join(str(arg) for arg in args)

    def make_api_url(self, uri, *args):
        return self.make_url('api', uri, *args)
                
    #######################
    # get-methods section #  
    #######################
        
    def get(self, uri: str):
        """
        gets entity of given entity_type with given entity_id
        returns dict
        can raise JSONDecodeError, HTTPError
        """ 
        response = self.s.get(self.make_api_url(uri))
        response.raise_for_status()
        return response.json()
    
    def get_all(self, uri: str):
        """
        gets all entities for given entity_type
        queries without visualizations, dashboards without widgets
        returns list of dicts
        can raise JSONDecodeError, HTTPError, TypeError
        """
        response = self.s.get(self.make_api_url(uri))
        response.raise_for_status()
        response = response.json()
        if type(response) == dict:
            entities = []
            page_count = int(response['count'] / response['page_size']) + 2
            for page in range(1, page_count):
                response = self.s.get(self.make_api_url(uri), params={'page': page}).json()
                entities.extend(response['results'])
        elif type(response) == list:
            entities = response
        else:
            raise TypeError('Response must be either dict or list')
        return entities
    
    def get_data_sources(self, include_view_only=True):
        """
        gets dictionary of Data Sources
        not used in other methods, just for info purpose
        """
        data_sources = self.get_all('data_sources')
        ds_dict = {ds.pop('name'): {key: ds[key] for key in ('id', 'type', 'view_only')}
                   for ds in data_sources if include_view_only or not ds['view_only']}
        return ds_dict 
    
    def get_query(self, query_id):
        """
        gets query with given id
        returns object of class Query
        """
        q = self.get(f'queries/{query_id}')
        return Query.from_dict(q)
    
    def get_queries(self, query_ids):
        """
        gets queries with given ids
        returns list of Query objects
        """
        queries = []
        for query_id in query_ids:
            queries.append(self.get_query(query_id))
        return queries
    
    def get_dashboard(self, slug):
        """
        gets dashboard with given slug
        returns object of class Dashboard
        """
        d = self.get(f'dashboards/{slug}')
        return Dashboard.from_dict(d)

    def get_dashboards(self, slugs):
        """
        gets dashboards with given slugs
        returns list of Dashboard objects
        """
        dashboards = []
        for slug in slugs:
            dashboards.append(self.get_dashboard(slug))
        return dashboards

    ########################
    # find-methods section #
    ########################


    def find_by_conditions(self, uri: str, conditions: dict, regex=False, return_slugs=False):
        """
        finds ids of uri, matching all given conditions (default exact matching, set regexp=True for re.search)
        """
        entities = self.get_all(uri)
        return _find_by_conditions(entities, conditions, regex, return_slugs)


    ########################
    # post-methods section #
    ########################
    
    def post(self, uri: str, data: dict):
        """
        posts some dict data to entity_type
        """
        res = self.s.post(self.make_api_url(uri), data=json.dumps(data))
        res.raise_for_status()
        return res.json()
    
    ##########################
    # delete-methods section #
    ##########################
             
    def delete(self, uri: str, data=None):
        if data is None:
            res = self.s.delete(self.make_api_url(uri))
        else:
            res = self.s.delete(self.make_api_url(uri), data=json.dumps(data))
        res.raise_for_status()
        return res.json()

    # def delete_entity(self, entity: RedashEntity):
    #     self.delete(entity.make_uri())
    #
    # def delete_dashboard(self, slug: str):
    #     d = self.get('dashboards', slug)
    #     if d['can_edit']:
    #         ans = input(f'Вы действительно хотите удалить дашборд {self.make_url("dashboard", slug)}? '
    #                     'Это действие невозможно отменить. [y/n]')
    #         if ans.lower() == 'y':
    #             self.delete('dashboards', slug)
    #         else:
    #             logger.error('Операция прервана')
    #             return
    #     else:
    #         logger.error(f'Нет прав на удаление дашборда {self.make_url("dashboard", slug)}')
    #         return
        
    ##########################
    # change-methods section #
    ##########################

    def _change_access(self, entity_type: str, entity_ids: list, user_ids: list, grant: bool):
        error_ids = set()
        for entity_id in entity_ids:
            try:
                for user_id in user_ids:
                    uri = f'{entity_type}/{entity_id}/acl'
                    data = {'user_id': user_id, 'access_type': 'modify'}
                    self.post(uri, data) if grant else self.delete(uri, data)
            except HTTPError:
                error_ids.add(entity_id)
        if len(error_ids) > 0:
            raise UserWarning(f'Не удалось изменить права для {entity_type} {error_ids}')

    def grant_access(self, entity_type: str, entity_ids: list, user_ids: list):
        self._change_access(entity_type, entity_ids, user_ids, grant=True)

    def limit_access(self, entity_type: str, entity_ids: list, user_ids: list):
        self._change_access(entity_type, entity_ids, user_ids, grant=False)

    def _change_entities(self, entity_type: str, entity_ids: list, data):
        error_ids = set()
        for entity_id in entity_ids:
            try:
                self.post(f'{entity_type}/{entity_id}', data)
            except HTTPError:
                error_ids.add(entity_id)
        if len(error_ids) > 0:
            raise UserWarning(f'Не удалось изменить {entity_type} {error_ids}')

    def archive_queries(self, query_ids: list):
        self._change_entities('queries', query_ids, {'is_archived': True})

    def restore_queries(self, query_ids: list):
        self._change_entities('queries', query_ids, {'is_archived': False})

    def tag_queries(self, query_ids: list, tags: list):
        self._change_entities('queries', query_ids, {'tags': tags})

    def schedule_queries(self, query_ids: list, interval_sec: int):
        schedule = {'interval': interval_sec,
                         'until': None,
                         'day_of_week': None,
                         'time': None}
        self._change_entities('queries', query_ids, {'schedule': schedule})
        
    def replace_query_sql(self, query_ids: list, str_from, str_to, regex=False):
        queries = self.get_queries(query_ids)
        queries = [q.replace_sql(str_from, str_to, regex) for q in queries]
        for q in queries:
            self._change_entities('queries', [q.id], {'query': q.query})


def _test_connection(url, s):
    r = s.get(f'{url}/api/queries')
    r.raise_for_status()
    r.json()


def _find_by_conditions(entities: list, conditions: dict, regex=False, return_slugs=False):
    entities_filtered = []
    for entity in entities:
        if regex:
            match = all(re.search(item[1], entity.get(item[0], '')) is not None for item in conditions.items())
        else:
            match = all(item in entity.items() for item in conditions.items())
        if match:
            entities_filtered.append(entity)

    if return_slugs:
        return [entity.get('slug') for entity in entities_filtered]
    else:
        return [entity.get('id') for entity in entities_filtered]


