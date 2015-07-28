import datetime
import json
import logging
import pprint
import re
import threading
import time

import sqlalchemy as sa

from sgevents import EventLog

from . import fields
from .api3.create import Api3CreateOperation
from .entity import EntityType
from .events import EventProcessor
from .exceptions import EntityMissing
from .logs import log_globals
from .scanner import Scanner
from .utils import log_exceptions

log = logging.getLogger(__name__)


class Cache(object):

    def __init__(self, db, spec):
        
        self.db = db
        self.metadata = sa.MetaData(bind=db)

        self._entity_types = {}
        for name, fields in spec.iteritems():
            fields['id'] = 'number'
            self._entity_types[name] = EntityType(self, name, fields)

        self._construct_schema()

    def __getitem__(self, key):
        try:
            return self._entity_types[key]
        except KeyError as e:
            raise EntityMissing(e.args[0])
    
    def get(self, *args):
        return self._entity_types.get(*args)

    def __contains__(self, key):
        return key in self._entity_types
    
    def _construct_schema(self):
        self.metadata.reflect()
        for entity in self._entity_types.itervalues():
            entity._construct_schema()

    def create_or_update(self, type_name, data, allow_id=False, **kwargs):
        request = {
            'type': type_name,
            'fields': [{'field_name': k, 'value': v} for k, v in data.iteritems()],
            'return_fields': ['id'],
        }
        op = Api3CreateOperation(request, allow_id=allow_id)
        op(self, **kwargs)
        return op

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

    def watch(self, last_id=None, last_time=None, auto_last_id=False, idle_delay=5.0, async=False):

        if async:
            thread = threading.Thread(target=self.watch, args=(last_id, last_time, auto_last_id, idle_delay))
            thread.daemon = True
            thread.start()
            return thread

        if auto_last_id:
            last_id, last_time = self.get_last_event()

        self.event_log = EventLog(last_id=last_id, last_time=last_time)
        self.event_processor = EventProcessor(self)

        while True:
            try:
                for event in self.event_log.iter_events(idle_delay=idle_delay):
                    log_globals.meta = {'event': event.id}
                    log.info(event.summary)
                    try:
                        handler = self.event_processor.get_handler(event)
                        if not handler:
                            continue
                        with self.db.begin() as con:
                            handler(con)
                    except:
                        log.exception('error during event %d:\n%s' % (event.id, event.dumps(pretty=True)))
            except:
                # NOTE: The event log may have corrupted its ID tracking.
                log.exception('error during event iteration; sleeping for 10s')
                time.sleep(10)

    def scan(self, interval=None, last_time=None, auto_last_id=False, async=False):
        
        if async:
            thread = threading.Thread(target=self.scan, args=(interval, last_time, auto_last_id))
            thread.daemon = True
            thread.start()
            return thread

        if auto_last_id:
            last_id, last_time = self.get_last_event()

        self.scanner = Scanner(self, last_time=last_time)
        while True:
            try:
                self.scanner.scan(interval)
                if not interval:
                    break # only need to get through one
            except:
                log.exception('error during scan; sleeping for 30s')
                time.sleep(30)




