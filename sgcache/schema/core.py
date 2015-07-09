import logging
import re
import threading
import datetime
import pprint
import json

import sqlalchemy as sa

from .entity import EntityType
from . import fields
from ..apimethods.read import ReadHandler
from ..apimethods.create import CreateHandler
from ..exceptions import EntityMissing
from ..eventlog import EventLog
from ..utils import log_exceptions


log = logging.getLogger(__name__)


class Schema(object):

    def __init__(self, db, spec):
        
        self.db = db
        self.spec = spec
        self.metadata = sa.MetaData(bind=db)

        self._entity_types = {}
        for name, fields in self.spec.iteritems():
            fields['id'] = 'number'
            self._entity_types[name] = EntityType(self, name, fields)

        self._create_sql()

    def __getitem__(self, key):
        try:
            return self._entity_types[key]
        except KeyError as e:
            raise EntityMissing(e.args[0])
    
    def __contains__(self, key):
        return key in self._entity_types
    
    def _create_sql(self):
        self.metadata.reflect()
        for entity in self._entity_types.itervalues():
            entity._create_sql()

    def read(self, request):
        handler = ReadHandler(request)
        return handler(self)

    def create(self, request, data=None, allow_id=False, **kwargs):

        if data is not None:
            request = {
                'type': request,
                'fields': [{'field_name': k, 'value': v} for k, v in data.iteritems()],
                'return_fields': ['id'],
            }
        
        handler = CreateHandler(request, allow_id=allow_id)
        return handler(self, **kwargs)

    def watch(self, async=False):

        if async:
            thread = threading.Thread(target=self.watch)
            thread.daemon = True
            thread.start()
            return thread

        self.event_log = EventLog(self, auto_last_id=True)
        while True:
            for events in self.event_log.iter():
                if not events:
                    continue
                with self.db.begin() as con:
                    self._process_events(con, events)

    def _process_events(self, con, events):
        for event in events:
            try:
                self._process_event(con, event)
            except:
                log.exception('error during event %d:\n%s' % (event['id'], json.dumps(event, sort_keys=True, indent=4)))


    def _process_event(self, con, event):

        event_type = event['event_type']
        event_id = event['id']
        event_entity = event.get('entity')

        summary_parts = ['%s %d' % (event_type, event_id)]
        if event_entity:
            summary_parts.append('on %s %d' % (event_entity['type'], event_entity['id']))
            if event_entity.get('name'):
                summary_parts.append('"%s"' % event_entity['name'])
        summary = ' '.join(summary_parts)

        domain, entity_type_name, event_subtype = event_type.split('_', 2)
        if domain != 'Shotgun':
            log.info('Skipping %s; not in Shotgun domain' % summary)
            return

        entity_type = self._entity_types.get(entity_type_name)
        if entity_type is None:
            log.info('Skipping %s; unknown entity type' % summary)
            return

        func = getattr(self, '_process_%s_event' % event_subtype.lower(), None)
        if func is None:
            log.info('Skipping %s; unknown event type' % summary)
            return

        log.info('Processing %s' % summary)
        func(con, event, entity_type)

    def _process_new_event(self, con, event, entity_type):
        '''
        {u'attribute_name': None,
         u'created_at': u'2015-07-09T19:33:37Z',
         u'entity': {u'id': 67378, u'name': u'something', u'type': u'Task'},
         u'event_type': u'Shotgun_Task_New',
         u'id': 2011530,
         u'meta': {u'entity_id': 67378,
                   u'entity_type': u'Task',
                   u'type': u'new_entity'},
         u'project': {u'id': 66, u'name': u'Testing Sandbox', u'type': u'Project'},
         u'type': u'EventLogEntry'}
        '''

        # we need to fetch all of the data from the server. bleh
        entities = self.event_log.api.call('read', {
            "type": entity_type.type_name,
            "return_fields": entity_type.fields.keys(), 
            "filters": {
                "conditions": [{
                    'path': 'id',
                    'relation': 'is',
                    'values': [event['entity']['id']],
                }],
                "logical_operator": "and",
            },
            "paging": {
                "current_page": 1, 
                "entities_per_page": 1,
            },
            "return_only": "active", 
        })['entities']

        if not entities:
            log.warning('Could not find "new" %s %d' % (entity_type.type_name, event['entity']['id']))
            return

        print 'CREATED', entities[0]
        self.create(entity_type.type_name, data=entities[0], allow_id=True, con=con, extra={
            '_last_log_event_id': event['id'],
        })

    def _process_change_event(self, con, event, entity_type):
        '''
        {u'attribute_name': u'color',
         u'created_at': u'2015-07-09T19:33:37Z',
         u'entity': {u'id': 67378, u'name': u'something', u'type': u'Task'},
         u'event_type': u'Shotgun_Task_Change',
         u'id': 2011531,
         u'meta': {u'attribute_name': u'color',
                   u'entity_id': 67378,
                   u'entity_type': u'Task',
                   u'field_data_type': u'color',
                   u'in_create': True,
                   u'new_value': u'pipeline_step',
                   u'old_value': None,
                   u'type': u'attribute_change'},
         u'project': {u'id': 66, u'name': u'Testing Sandbox', u'type': u'Project'},
         u'type': u'EventLogEntry'}

        OR

        {u'attribute_name': u'tasks',
         u'created_at': u'2015-07-09T23:00:10Z',
         u'entity': {u'id': 7080, u'name': u'002_001', u'type': u'Shot'},
         u'event_type': u'Shotgun_Shot_Change',
         u'id': 2011759,
         u'meta': {u'actual_attribute_changed': u'Task.entity',
                   u'added': [{u'id': 67380,
                               u'name': u'newtask3',
                               u'status': u'wtg',
                               u'type': u'Task',
                               u'uuid': u'3fc23e92-268e-11e5-ac19-0025900054a4',
                               u'valid': u'valid'}],
                   u'attribute_name': u'tasks',
                   u'entity_id': 67380,
                   u'entity_type': u'Task',
                   u'field_data_type': u'entity',
                   u'in_create': True,
                   u'original_event_log_entry_id': 2011758,
                   u'removed': [],
                   u'type': u'attribute_change'},
         u'project': {u'id': 66, u'name': u'Testing Sandbox', u'type': u'Project'},
         u'type': u'EventLogEntry'}


        '''

        data = event['entity'].copy()
        if event.get('project'):
            data['project'] = event['project']

        # use an internal syntax for adding or removing from multi-entities
        added = event['meta'].get('added')
        removed = event['meta'].get('removed')
        if added or removed:
            data[event['attribute_name']] = {'__added__': added, '__removed__': removed}
        else:
            data[event['attribute_name']] = event['meta']['new_value']

        self.create(entity_type.type_name, data=data, allow_id=True, con=con, extra={
            '_last_log_event_id': event['id'],
        })


