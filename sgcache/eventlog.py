import time
import pprint
import logging

import sqlalchemy as sa

from shotgun_api3_registry import get_args as get_sg_args

from .sgapi import SGAPI


log = logging.getLogger(__name__)


class EventLog(object):

    def __init__(self, schema, api=None, last_id=None, auto_last_id=False):
        
        self.schema = schema
        self.api = api or SGAPI(*get_sg_args()) # TODO: force use of non-cache args
        
        self.last_id = last_id or None
        self.last_time = None
        self.auto_last_id = auto_last_id

    def iter(self, batch_size=100, delay=3.0):
        while True:
            e = self.read(batch_size)
            if e:
                yield e
            else:
                time.sleep(delay)

    def read(self, batch_size=100):

        # detect from existing data
        # we look for the largest _last_log_event_id, and latest _cache_updated_at
        # across all tables
        if not self.last_id and self.auto_last_id:
            for entity_type in self.schema._entity_types.itervalues():
                row = sa.select([
                    sa.func.max(entity_type.table.c._last_log_event_id),
                    sa.func.max(entity_type.table.c._cache_updated_at),
                ]).execute().fetchone()
                self.last_id = max(
                    self.last_id or 0,
                    row[0] or 0
                ) or None
                self.last_time = max(
                    self.last_time or '',
                    row[1].replace(microsecond=0).isoformat('T') + 'Z' if row[1] else ''
                ) or None
            log.info('auto-detected start: ID %s, time %s' % (self.last_id or None, self.last_time))

        if self.last_id:
            entities = self._read(batch_size, filters=[{
                'path': 'id',
                'relation': 'greater_than',
                'values': [self.last_id],
            }])
        else:
            if self.last_time:
                # everything since the last time
                entities = self._read(batch_size, filters=[{
                    'path': 'created_at',
                    'relation': 'greater_than',
                    'values': [self.last_time],
                }])
            else:
                # the last event
                entities = self._read(1, sorts=[{
                    'field_name': 'created_at',
                    'direction': 'desc',
                }])

        if entities:
            self.last_id = max(self.last_id or 0, max([e['id'] for e in entities]))
            self.last_time = max(self.last_time or '', max([e['created_at'] for e in entities]))

        return entities or None

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








