import datetime
import json
import logging
import pprint
import re
import threading
import time

import collections

import sqlalchemy as sa

from sgevents import EventLog

from . import fields
from .api3.create import Api3CreateOperation
from .entity import EntityType
from .events import EventProcessor
from .exceptions import EntityMissing
from .logs import log_globals
from .scanner import Scanner
from .utils import log_exceptions, get_shotgun

log = logging.getLogger(__name__)


class Cache(collections.Mapping):

    """The master cache model from which all operations tend to start.

    :param db: SQLAlchemy engine to use for cache.
    :param schema: The :class:`~.Schema` to cache.

    """

    def __init__(self, db, schema):
        self.db = db
        self.metadata = sa.MetaData(bind=db)
        self.schema = schema

        # Build model objects from the schema; these will not be complete
        # until we reflect the database below.
        self._entity_types = {}
        for name, entity_schema in schema.iteritems():
            self._entity_types[name] = EntityType(self, name, entity_schema)

        # Reflect the database and issue any required DDL.
        self.metadata.reflect()
        for entity in self._entity_types.itervalues():
            entity._construct_schema()

    def __getitem__(self, key):
        try:
            return self._entity_types[key]
        except KeyError as e:
            raise EntityMissing(e.args[0])
    
    def __iter__(self):
        return iter(self._entity_types)

    def __len__(self):
        return len(self._entity_types)

    def create_or_update(self, type_name, data, create_with_id=False, **kwargs):
        """Create or update an entity, with an API eerily similar to ``python_api3``.

        This is a wrapper around :class:`.Api3CreateOperation`.
        
        :param str type_name: The name of the type of entity to create/update.
        :param dict data: The key-value data for that entity.
        :param bool create_with_id: Should ``id`` be allowed within the ``data`` param?
            If not, then the entity must already exist, and this is an ``update``.
            If so, then the entity will be updated if it exists, or will be
            created if not (and it is assumed that ``data`` represents a complete
            view of that entity).
        :param \**kwargs: Options to pass to :meth:`.Api3CreateOperation.run`.
        :return: The :class:`~.Api3CreateOperation`, which can be inspected to
            see if the entity existed or not.

        ::

            >>> res = cache.create_or_update('Task', data)
            >>> res.entity_exists
            False

        """
        request = {
            'type': type_name,
            'fields': [{'field_name': k, 'value': v} for k, v in data.iteritems()],
            'return_fields': ['id'],
        }
        op = Api3CreateOperation(request, create_with_id=create_with_id)
        op.run(self, **kwargs)
        return op

    def get_last_event(self):
        """Get tuple of ``(last_id, last_time)`` stored in the cache.

        This is optionally used to seed :meth:`watch` and :meth:`scan`.

        """
        last_id = None
        last_time = None
        for entity_type in self._entity_types.itervalues():
            row = sa.select([
                sa.func.max(entity_type.table.c._last_log_event_id),
                sa.func.max(entity_type.table.c._cache_updated_at),
            ]).execute().fetchone()

            # We can max(None, 1), so this is ok...
            last_id = max(last_id, row[0]) 
            # ... but datetime does not compare against None directly.
            last_time = max(last_time, row[1]) if (last_time and row[1]) else (last_time or row[1])

        return last_id, last_time

    def watch(self, last_id=None, last_time=None, auto_last_id=False, idle_delay=5.0, async=False):
        """Watch the Shotgun event log, and process events.

        :param int last_id: Last seen event ID to start processing at.
        :param datetime.datetime last_time: Last seen cache time to start processing at.
        :param bool auto_last_id: Should we use :meth:`get_last_event`
            to determine where to start processing?
        :param float idle_delay: Seconds between polls of the event log.
        :param bool async: Should this be run in a thread?

        :returns: ``threading.Thread`` if ``async`` is true.

        """

        if async:
            thread = threading.Thread(target=self.watch, args=(last_id, last_time, auto_last_id, idle_delay))
            thread.daemon = True
            thread.start()
            return thread

        if auto_last_id:
            last_id, last_time = self.get_last_event()

        self.event_log = EventLog(shotgun=get_shotgun('sgapi'), last_id=last_id, last_time=last_time)
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

    def scan(self, interval=None, last_time=None, auto_last_time=False, async=False, **kwargs):
        """Periodically scan Shotgun for updated entities.

        :param float interval: Seconds between scans; ``None`` implies a single scan.
        :param datetime.datetime last_time: When to scan for updates since; ``None``
            implies a complete scan of Shotgun.
        :param bool auto_last_time: Should we use :meth:`get_last_event` to
            determine when to scan since?
        :param bool async: Should this be run in a thread?

        :returns: ``threading.Thread`` if ``async`` is true.

        """

        if async:
            thread = threading.Thread(target=self.scan, args=(interval, last_time, auto_last_time), kwargs=kwargs)
            thread.daemon = True
            thread.start()
            return thread

        if auto_last_time:
            last_id, last_time = self.get_last_event()

        self.scanner = Scanner(self, last_time=last_time, **kwargs)
        while True:
            try:
                self.scanner.scan(interval)
                if not interval:
                    break # only need to get through one
            except:
                log.exception('error during scan; sleeping for 30s')
                time.sleep(30)




