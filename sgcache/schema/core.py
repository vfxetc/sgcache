import logging
import re
import threading
import datetime
import pprint
import json

import sqlalchemy as sa

from sgevents import EventLog


from . import fields
from ..apimethods.create import CreateHandler
from ..apimethods.read import ReadHandler
from ..exceptions import EntityMissing
from ..logs import log_globals
from ..utils import log_exceptions
from .entity import EntityType


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

    def get_last_event(self):
        last_id = 0
        last_time = None
        for entity_type in self._entity_types.itervalues():
            row = sa.select([
                sa.func.max(entity_type.table.c._last_log_event_id),
                sa.func.max(entity_type.table.c._cache_updated_at),
            ]).execute().fetchone()
            last_id = max(
                last_id or 0,
                row[0] or 0
            ) or None
            last_time = max(
                last_time or '',
                row[1].replace(microsecond=0).isoformat('T') + 'Z' if row[1] else ''
            ) or None
        return last_id, last_time

    def watch(self, async=False, auto_last_id=False):

        if async:
            thread = threading.Thread(target=self.watch, kwargs={'auto_last_id': auto_last_id})
            thread.daemon = True
            thread.start()
            return thread

        if auto_last_id:
            last_id, last_time = self.get_last_event()
        else:
            last_id = last_time = None

        self.event_log = EventLog(last_id=last_id, last_time=last_time)
        while True:
            for event in self.event_log.iter_events():
                log_globals.meta = {'event': event.id}
                log.info(event.summary)
                try:
                    handler = self._get_event_handler(event)
                    if not handler:
                        continue
                    with self.db.begin() as con:
                        handler(con)
                except:
                    log.exception('error during event %d:\n%s' % (event.id, event.dumps(pretty=True)))

    def _get_event_handler(self, event):

        if event.domain != 'Shotgun':
            log.info('skipping event; not in Shotgun domain')
            return

        entity_type = self._entity_types.get(event.entity_type)
        if entity_type is None:
            log.info('skipping event; unknown entity type %s' % event.entity_type)
            return

        func = getattr(self, '_process_%s_event' % event.subtype.lower(), None)
        if func is None:
            log.info('skipping event; unknown event subtype %s' % (event.subtype))
            return

        return lambda con: func(con, event, entity_type)


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
        entity = self.event_log.shotgun.find_one(entity_type.type_name, [
            ('id', 'is', event.entity_id),
        ], entity_type.fields.keys())

        if not entity:
            log.warning('Could not find "new" %s %d' % (entity_type.type_name, event.entity_id))
            return

        # print 'CREATED', entities[0]
        self.create(entity_type.type_name, data=entity, allow_id=True, con=con, extra={
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

        OR (on a backref)

        {
            "attribute_name": "tasks", 
            "created_at": "2015-07-09T23:00:10Z", 
            "entity": {
                "id": 7080, 
                "name": "002_001", 
                "type": "Shot"
            }, 
            "event_type": "Shotgun_Shot_Change", 
            "id": 2011759, 
            "meta": {
                "actual_attribute_changed": "Task.entity", 
                "added": [
                    {
                        "id": 67380, 
                        "name": "newtask3", 
                        "status": "wtg", 
                        "type": "Task", 
                        "uuid": "3fc23e92-268e-11e5-ac19-0025900054a4", 
                        "valid": "valid"
                    }
                ], 
                "attribute_name": "tasks", 
                "entity_id": 67380, 
                "entity_type": "Task", 
                "field_data_type": "entity", 
                "in_create": true, 
                "original_event_log_entry_id": 2011758, 
                "removed": [], 
                "type": "attribute_change"
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry"
        }

        OR (after a retirement; note the NULL entity):

        {
            "attribute_name": "retirement_date", 
            "created_at": "2015-07-13T21:54:01Z", 
            "entity": null, 
            "event_type": "Shotgun_Task_Change", 
            "id": 2017315, 
            "meta": {
                "attribute_name": "retirement_date", 
                "entity_id": 67519, 
                "entity_type": "Task", 
                "new_value": "2015-07-13 21:54:01 UTC", 
                "old_value": null, 
                "type": "attribute_change"
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry", 
            "user": {
                "id": 108, 
                "name": "Mike Boers", 
                "type": "HumanUser"
            }
        }

        BUT:

            >>> sg.find_one('Task', [('$FROM$EventLogEntry.entity.id', 'is', 2017315)], [], retired_only=True)
            {'type': 'Task', 'id': 67519}


        '''

        data = event.entity.copy()
        if event.get('project'):
            data['project'] = event['project']

        # use an internal syntax for adding or removing from multi-entities
        added = event.meta.get('added')
        removed = event.meta.get('removed')
        if added or removed:
            data[event['attribute_name']] = {'__added__': added, '__removed__': removed}
        else:
            data[event['attribute_name']] = event['meta']['new_value']

        self.create(entity_type.type_name, data=data, allow_id=True, con=con, extra={
            '_last_log_event_id': event['id'],
        })

    def _process_retirement_event(self, con, event, entity_type):
        '''
        {
            "attribute_name": null, 
            "created_at": "2015-07-13T22:32:35Z", 
            "entity": null, 
            "event_type": "Shotgun_Task_Retirement", 
            "id": 2017525, 
            "meta": {
                "class_name": "Task", 
                "display_name": "another to delete", 
                "entity_id": 67531, 
                "entity_type": "Task", 
                "id": 67531, 
                "retirement_date": "2015-07-13 22:32:35 UTC", 
                "type": "entity_retirement"
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry", 
            "user": {
                "id": 108, 
                "name": "Mike Boers", 
                "type": "HumanUser"
            }
        }
        '''
        pass

    def _process_revival_event(self, con, event, entity_type):
        '''
        {
            "attribute_name": null, 
            "created_at": "2015-07-13T22:34:21Z", 
            "entity": {
                "id": 67531, 
                "name": "another to delete", 
                "type": "Task"
            }, 
            "event_type": "Shotgun_Task_Revival", 
            "id": 2017561, 
            "meta": {
                "class_name": "Task", 
                "display_name": "another to delete", 
                "entity_id": 67531, 
                "entity_type": "Task", 
                "id": 67531
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry", 
            "user": {
                "id": 108, 
                "name": "Mike Boers", 
                "type": "HumanUser"
            }
        }
        '''
        pass



