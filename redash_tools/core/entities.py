import logging
import json
from string import Template
import re
import os
from requests import HTTPError

logger = logging.getLogger(__name__)


class RedashEntity:
    __slots__ = 'ent_type', 'id'

    def __init__(self, ent_type, id=None):
        self.ent_type = ent_type
        self.id = id

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.make_uri()}>'
    
    def __str__(self):
        return json.dumps(self.to_dict(), sort_keys=True)

    def __eq__(self, other):
        return all(getattr(self, field, None) == getattr(other, field, None) for field in self.__slots__)

    def make_uri(self):
        return self.ent_type if self.id is None else f'{self.ent_type}/{self.id}'

    def sort_func(self):
        return self.id is None, self.id
    
    @classmethod
    def from_dict(cls, data):
        filtered_dict = {}
        for c in cls.mro():
            if hasattr(c, '__slots__'):
                for field in set(c.__slots__) & set(data):
                    filtered_dict[field] = data.get(field)
        return cls(**filtered_dict)

    @classmethod
    def from_file(cls, path, id):
        entity_dict = {'id': id}
        with open(os.path.join(path, f'{id}.json'), 'r',  encoding='utf-8') as file:
            entity_dict.update(json.load(file))
        return cls.from_dict(entity_dict)

    def to_dict(self, drop_fields=()):
        self_dict = {}
        for field in (set(self.__slots__) - set(drop_fields)):
            temp = getattr(self, field, None)
            if type(temp) == list:
                self_dict[field] = [t.to_dict() if type(t) in (Widget, Visualization, Query) else t for t in temp]
            else:
                self_dict[field] = temp.to_dict() if type(temp) in (Widget, Visualization, Query) else temp
        return self_dict
    
    def to_file(self, path):
        filename = os.path.join(path, f'{self.id}.json')
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(self.to_dict(), file, sort_keys=True, indent=4)
        return filename
    
    def to_redash(self, redash_session, try_to_update=False):
        uri = self.make_uri() if try_to_update else self.ent_type
        try:
            remote_entity_dict = redash_session.post(uri, self.to_dict())
        except:
            logger.error(f'Не удалось {"обновить" if try_to_update else "создать"} {uri}')
            raise
        return remote_entity_dict


class Taggable(RedashEntity):
    __slots__ = 'tags',

    def __init__(self, ent_type, id=None, tags=None):
        super().__init__(ent_type, id)
        self.tags = set()
        if tags is not None:
            self.add_tags(tags)

    def add_tags(self, tags):
        if type(tags) in (str, int):
            self.tags.add(str(tags))
        elif type(tags) in (set, list, tuple):
            [self.add_tags(tag) for tag in tags]
        else:
            raise TypeError(f'Wrong type for tag {tags}: {type(tags)}')
        return self

    def remove_tags(self, tags):
        if type(tags) in (str, int):
            self.tags.discard(str(tags))
        elif type(tags) in (set, list, tuple):
            [self.remove_tags(tag) for tag in tags]
        else:
            raise TypeError(f'Wrong type for tag {tags}: {type(tags)}')
        return self


class Query(Taggable):
    __slots__ = 'data_source_id', 'query', 'name', 'schedule', 'visualizations', 'options'
    
    def __init__(self,
                 data_source_id,
                 query,
                 id=None,
                 name=None,
                 schedule=None,
                 tags=None,
                 visualizations=None,
                 options=None
                 ):
        super().__init__(ent_type='queries', id=id, tags=tags)
        self.data_source_id = data_source_id
        self.query = query
        self.name = name or 'New rtQuery'
        self.schedule = schedule
        self.visualizations = []
        if visualizations is not None:
            for v in visualizations:
                self.add_visualization(Visualization.from_dict(v))
        self.visualizations.sort(key=lambda v: v.sort_func())
        self.options = options or {}

    def match(self, other):
        return self.data_source_id == other.data_source_id and self.query == other.query

    def _update_query_id(self, new_id):
        self.id = new_id
        for v in self.visualizations:
            v.query_id = new_id
        return self
    
    def to_dict(self):
        return super().to_dict()
    
    def to_redash(self, redash_session, try_to_update=False):
        remote_query = Query.from_dict(super().to_redash(redash_session, try_to_update))
        self._update_query_id(remote_query.id)
        remote_query_default_vis_id = remote_query.visualizations[0].id
        for v in remote_query.visualizations[1:]:
            try:
                redash_session.delete(v.make_uri())
            except HTTPError:
                print('exception')
        remote_query.visualizations = [remote_query.visualizations[0]]
        visualizations = []
        for v in self.visualizations:
            visualizations.append(Visualization.from_dict(v.to_dict()))  # to avoid mutating of initial vis
            print(visualizations)
        visualizations[0].id = remote_query_default_vis_id
        visualizations[0].query_id = remote_query.id
        remote_query.visualizations[0] = Visualization.from_dict(visualizations[0].to_redash(redash_session,
                                                                                             try_to_update=True))
        for v in visualizations[1:]:
            v.query_id = remote_query.id
            remote_query.visualizations.append(Visualization.from_dict(v.to_redash(redash_session,
                                                                                   try_to_update=False)))
        return remote_query
        
    def to_template(self, param_names):
        return QueryTemplate(self, param_names)
  
    def set_schedule(self, interval_sec):
        self.schedule = {'interval': interval_sec, 
                         'until': None, 
                         'day_of_week': None,
                         'time': None}
        return self
        
    def add_visualization(self, visualization):
        visualization.query_id = self.id
        self.visualizations.append(visualization)
        return visualization

    def replace_sql(self, str_from, str_to, regex=False):
        if regex:
            self.query = re.sub(str_from, str_to, self.query, re.DOTALL)
        else:
            self.query = self.query.replace(str_from, str_to)
        return self
        
        
class Dashboard(Taggable):
    __slots__ = 'slug', 'name', 'widgets', 'queries'
    
    def __init__(self,
                 slug,
                 name=None,
                 id=None,
                 tags=None, 
                 widgets=None):
        super().__init__(ent_type='dashboards', id=id, tags=tags)
        self.slug = slug
        self.name = name or slug
        self.widgets = []
        self.queries = []
        if widgets is not None:
            self.widgets = [Widget.from_dict(w) for w in widgets]
            visualizations = []
            queries = []
            for w in widgets:
                v = w.get('visualization')
                if v is not None:
                    v['query_id'] = v['query']['id']
                    visualizations.append(Visualization.from_dict(v))
                    queries.append(Query.from_dict(v['query']))
            self.queries = list({q.id: q for q in queries}.values())  # deduplication
            for q in self.queries:
                [q.add_visualization(v) for v in visualizations if v.query_id == q.id]
                q.visualizations.sort(key=lambda v: v.sort_func())
            self.queries.sort(key=lambda q: q.sort_func())
            self.widgets.sort(key=lambda w: w.sort_func())


    @classmethod
    def from_file(cls, path, slug):
        entity_dict = {'slug': slug}
        with open(os.path.join(path, f'{slug}.json'), 'r',  encoding='utf-8') as file:
            entity_dict.update(json.load(file))
        return cls.from_dict(entity_dict)

    def _update_id(self, redash_session):
        d = redash_session.get(f'{self.ent_type}/{self.slug}')
        if d['is_archived']:
            logger.error(
                f'Дашборд {redash_session.url}/dashboard/{self.slug} заархивирован и не может быть восстановлен')
            raise UserWarning
        if not d['can_edit']:
            logger.error(f'Нет прав на редактирование дашборда {redash_session.url}/dashboard/{self.slug}')
            raise UserWarning
        self.id = d['id']
        for w in self.widgets:
            w.dashboard_id = self.id
        return self

    def _update_visualization_ids(self, ids_matching):
        for w in self.widgets:
            if w.visualization_id is not None:
                w.visualization_id = ids_matching.get(w.visualization_id)
        return self

    # def to_dict(self):
    #     return super().to_dict()
    
    def to_redash(self, redash_session, try_to_update=False):
        if not try_to_update:
            remote_dict = redash_session.post('dashboards', {'name': self.slug})  # try to occupy slug
            remote_dict = redash_session.post(f'dashboards/{remote_dict["id"]}', {'name': self.name})  # rename
            remote_db = Dashboard.from_dict(remote_dict)
            ids_matching = {}
            for q in self.queries:
                remote_q = q.to_redash(redash_session, try_to_update=False)
                remote_db.queries.append(remote_q)
                for v, remote_v in zip(q.visualizations, remote_q.visualizations):
                    ids_matching[v.id] = remote_v.id
            for w in self.widgets:
                w_copy = Widget.from_dict(w.to_dict())  # to avoid mutating of initial widgets
                w_copy.dashboard_id = remote_db.id
                if w_copy.visualization_id is not None:
                    w_copy.visualization_id = ids_matching.get(w_copy.visualization_id)
                remote_db.widgets.append(Widget.from_dict(w_copy.to_redash(redash_session,
                                                                       try_to_update=True)))
        else:
            remote_db = Dashboard.from_dict(super().to_redash(redash_session, try_to_update=True))
            print(remote_db.slug)
            print(remote_db.widgets)
            ids_matching = {}
            for q in self.queries:
                remote_q = q.to_redash(redash_session, try_to_update=True)
                remote_db.queries.append(remote_q)
                for v, remote_v in zip(q.visualizations, remote_q.visualizations):
                    ids_matching[v.id] = remote_v.id
            for w in remote_db.widgets:
                try:
                    redash_session.delete(w.make_uri())
                except HTTPError:
                    print('exception')
            print(remote_db.widgets)
            for w in self.widgets:
                w_copy = Widget.from_dict(w.to_dict())  # to avoid mutating of initial widgets
                w_copy.dashboard_id = remote_db.id
                if w_copy.visualization_id is not None:
                    w_copy.visualization_id = ids_matching.get(w_copy.visualization_id)
                remote_db.widgets.append(Widget.from_dict(w_copy.to_redash(redash_session,
                                                                       try_to_update=True)))
            print(remote_db.widgets)
        return remote_db


    def create_slug(self, redash_session):
        redash_session.post('dashboards', {'name': self.slug})
        
    def to_template(self, param_names):
        return DashboardTemplate(self, param_names)

    def set_schedule(self, interval_sec):
        for q in self.queries:
            q.set_schedule(interval_sec)
        return self

    def change_parameter_level(self, parameter_name, level='dashboard', title=None):
        levels = ('dashboard', 'widget')
        if level not in levels:
            logger.error(f'Допустимые значения level: {levels}')
            return
        for widget in self.widgets:
            if 'parameterMappings' in widget.options.keys():
                if parameter_name in widget.options['parameterMappings'].keys():
                    widget.options['parameterMappings'][parameter_name] = {'type': '{level}-level',
                                                                    'mapTo': parameter_name,
                                                                    'name': parameter_name,
                                                                    'title': title or parameter_name}
        return self

    def publish(self, redash_session):
        redash_session.post(self.make_uri(), {'is_draft': False})

    def unpublish(self, redash_session):
        redash_session.post(self.make_uri(), {'is_draft': True})


class Visualization(RedashEntity):
    __slots__ = 'query_id', 'type', 'options', 'name'
    
    def __init__(self, type, query_id=None, options=None, id=None, name=None):
        super().__init__('visualizations', id)
        self.query_id = query_id
        self.type = type
        self.options = options or {}
        self.name = name or 'New rtVisualization'

    def match(self, other):
        return self.type == other.type and self.options == other.options


class Widget(RedashEntity):
    __slots__ = 'dashboard_id', 'visualization_id', 'text', 'width', 'options'
    
    def __init__(self,
                 dashboard_id,
                 options,
                 visualization_id=None,
                 text=None,
                 id=None,
                 width=None):
        super().__init__('widgets', id)
        self.dashboard_id = dashboard_id
        self.visualization_id = visualization_id
        self.text = text if text != '' else None
        self.options = options
        self.width = width or 1

    @classmethod
    def from_dict(cls, data):
        if 'visualization' in data:
            data['visualization_id'] = data['visualization'].get('id')
        return super().from_dict(data)


class QueryTemplate:
    def __init__(self, query, param_names):
        self.data_source_id = query.data_source_id
        sql = query.query
        for p in param_names:
            pattern = '{{ *' + p + ' *}}'
            sql = re.sub(pattern, f'${p}', sql)
        self.query = Template(sql)
        self.name = query.name
        self.tags = query.tags
        self.visualizations = query.visualizations
        self.options = query.options
        for p in self.options.get('parameters', []):
            if p.get('name') in param_names:
                self.options['parameters'].remove(p)
    
    def render(self, param_dict, custom_tags=None):
        query = Query(data_source_id=self.data_source_id,
                      query=self.query.substitute(param_dict),
                      name=self.name,
                      tags=self.tags,
                      options=self.options)
        query.visualizations = self.visualizations
        if custom_tags is not None:
            query.add_tags(custom_tags)
        return query

    # TODO: add methods for rendering template from dict and saving to dict
    
        
class DashboardTemplate:
    def __init__(self, dashboard, param_names, slug=None):
        self.slug = slug or dashboard.slug
        self.name = dashboard.name
        self.tags = dashboard.tags
        self.widgets = dashboard.widgets
        self.queries = [QueryTemplate(q, param_names) for q in dashboard.queries] 
    
    def render(self, param_dict, slug=None, name=None, custom_tags=None):
        slug = slug or self.slug
        name = name or self.name
        dashboard = Dashboard(slug=slug,
                              name=name,
                              tags=self.tags)
        dashboard.widgets = self.widgets
        dashboard.queries = [q.render(param_dict, custom_tags) for q in self.queries]
        if custom_tags is not None:
            dashboard.add_tags(custom_tags)
        return dashboard
