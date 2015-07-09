import time
import pprint

from shotgun_api3_registry import get_args as get_sg_args

from .sgapi import SGAPI


class EventLog(object):

    def __init__(self, schema, last_id=None, auto_last_id=False):
        
        self.schema = schema
        self.api = SGAPI(*get_sg_args()) # TODO: force use of non-cache args
        
        self.last_id = last_id or 0
        self.last_time = None
        self.auto_last_id = auto_last_id

        self.buffer = []

    def iter(self, batch_size=50, delay=3.0):
        while True:
            e = self.fetch_one(batch_size)
            if e:
                yield e
            else:
                time.sleep(delay)

    def fetch_one(self, batch_size):

        if self.buffer:
            return self.buffer.pop(0)

        # detect from existing data
        # we look for the largest _last_log_event_id, and latest _cache_updated_at
        # across all tables
        if not self.last_id and self.auto_last_id:
            for entity_type in self.schema._entity_types.itervalues():
                row = entity_type.table.select(
                    sa.func.max(entity_type.table.c._last_event_log_id),
                    sa.func.max(entity_type.table.c._cache_updated_at),
                ).execute().fetchone()
                self.last_id = max(self.last_id, row[0] or 0)
                self.last_time = max(self.last_time or row[1].isoformat() + 'Z') if row[1] else self.last_time

        if self.last_id:
            #print 'AFTER ID', self.last_id
            self.buffer = self._read(batch_size, filters=[{
                'path': 'id',
                'relation': 'greater_than',
                'values': [self.last_id],
            }])
        else:
            if self.last_time:
                #print 'AFTER', self.last_time
                # everything since the last time
                self.buffer = self._read(batch_size, filters=[{
                    'path': 'created_at',
                    'relation': 'greater_than',
                    'values': [self.last_time.isoformat() + 'Z'],
                }])
            else:
                # the last event
                #print 'LAST EVENT'
                self.buffer = self._read(1, sorts=[{
                    'field_name': 'created_at',
                    'direction': 'desc',
                }])

        if self.buffer:
            self.last_id = max(self.last_id or 0, max([e['id'] for e in self.buffer]))
            self.last_time = max(self.last_time or '', max([e['created_at'] for e in self.buffer]))

        return self.buffer.pop(0) if self.buffer else None

    def _read(self, limit, filters=None, sorts=None):
        res = self.api.call('read', {
            "type": "EventLogEntry",
            "return_fields": [
                'attribute_name',
                'created_at',
                'entity',
                'event_type',
                'meta',
                'project',
            ], 
            "filters": {
                "conditions": filters or [],
                "logical_operator": "and",
            },
            'sorts': sorts or [],
            "paging": {
                "current_page": 1, 
                "entities_per_page": limit,
            },
            "return_only": "active", 
        })
        return res['entities']

    def watch(self):
        '''
        
        ENTITY_CREATION:
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

        followed by many:

        ENTITY_CHANGE
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

        }
        '''
        for event in self.iter():
            pprint.pprint(event)










