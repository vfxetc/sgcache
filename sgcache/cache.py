import collections
import contextlib
import datetime
import functools
import json
import logging
import re
import threading
import time

import sqlalchemy as sa
from sqlalchemy.engine.base import Transaction as _sa_Transaction

from sgapi import TransportError
from sgevents import EventLog

from . import fields
from .api3.create import Api3CreateOperation
from .entity import EntityType
from .events import EventProcessor
from .exceptions import EntityMissing
from .logs import log_globals
from .scanner import Scanner
from .schema import Schema
from .utils import log_exceptions, get_shotgun, try_call_except_traceback


log = logging.getLogger(__name__)


class Cache(collections.Mapping):

    """The master cache model from which all operations tend to start.

    :param db: SQLAlchemy engine to use for cache.
    :param schema: The :class:`~.Schema` to cache.

    """

    def __init__(self, db=None, schema=None, config=None):

        if (config and (db or schema)) or ((db or schema) and not (db and schema)):
            raise ValueError('provide either config, or db and schema')

        if config:
            db = sa.create_engine(config['SQLA_URL'], echo=bool(config['SQLA_ECHO']))
            schema = Schema.from_yaml(config['SCHEMA'])

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

    @contextlib.contextmanager
    def db_connect(self, con=None):

        # If given a connection, use that.
        if con is not None:
            yield con

        else:
            with self.db.connect() as con:
                yield con

    @contextlib.contextmanager
    def db_begin(self, con=None):

        # If we have a "connection" that came from Engine.begin(),
        # then just pass it through.
        if con is not None and isinstance(con, _sa_Transaction):
            yield con

        # If we have a "real" connection, start a transaction.
        elif con is not None:
            with con.begin():
                yield con

        # Yield a combo connection/transaction.
        else:
            with self.db.begin() as con:
                yield con

    def __getitem__(self, key):
        try:
            return self._entity_types[key]
        except KeyError as e:
            raise EntityMissing(e.args[0])
    
    def __iter__(self):
        return iter(self._entity_types)

    def __len__(self):
        return len(self._entity_types)

    def filter_cacheable_data(self, type_name, data=None):

        if isinstance(type_name, dict):
            data = type_name.copy()
            type_name = data.pop('type')
        
        cacheable_data = {}
        if 'id' in data:
            cacheable_data['id'] = data.pop('id')
        data.pop('type', None)

        entity_type = self[type_name]
        for field_name, value in data.iteritems():
            field = entity_type.get(field_name)
            if field and field.is_cached():
                cacheable_data[field_name] = value

        return cacheable_data

    def filter_cacheable_entity(self, entity):
        type_ = entity['type']
        cacheable = self.filter_cacheable_data(entity)
        cacheable['type'] = type_
        return cacheable

    def create_or_update(self, type_name, data, create_with_id=False, source_event=None, **kwargs):
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
        op = Api3CreateOperation(request, create_with_id=create_with_id, source_event=source_event)
        op.run(self, **kwargs)
        return op

    def retire(self, type_name, entity_id, **kwargs):
        return self._set_active(type_name, entity_id, False, **kwargs)

    def revive(self, type_name, entity_id, **kwargs):
        return self._set_active(type_name, entity_id, True, **kwargs)

    def _set_active(self, type_name, entity_id, state, extra=None, source_event=None, con=None, strict=True):

        entity_type = self[type_name]

        data = self.filter_cacheable_data(type_name, extra) if extra else {}
        data['_active'] = bool(state)
        data['_cache_updated_at'] = datetime.datetime.utcnow() # TODO: isn't this automatic?
        if source_event:
            data['_last_log_event_id'] = source_event.id

        with self.db_begin(con) as con:
            res = con.execute(entity_type.table.update().where(entity_type.table.c.id == entity_id), **data)

        if strict and not res.rowcount:
            raise ValueError('cannot %s un-cached %s %d' % ('revive' if state else 'retire', type_name, entity_id))

        return bool(res.rowcount)

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
            thread = threading.Thread(target=functools.partial(try_call_except_traceback, self.watch, last_id, last_time, auto_last_id, idle_delay))
            thread.daemon = True
            thread.start()
            return thread

        if auto_last_id:
            last_id, last_time = self.get_last_event()

        # Ask for the updated_at of every entity that we care about.
        # This is used in the handling of "change" events.
        extra_fields = []
        for entity_name in self:
            extra_fields.append('entity.%s.updated_at' % entity_name)

        self.event_log = EventLog(shotgun=get_shotgun('sgapi'), last_id=last_id, last_time=last_time, extra_fields=extra_fields)
        self.event_processor = EventProcessor(self)

        io_error_count = 0
        error_count = 0

        while True:
            try:
                for event in self.event_log.iter_events_forever(idle_delay=idle_delay):
                    
                    io_error_count = error_count = 0
                    log_globals.meta = {'event': event['id']}

                    try:
                        log.info(event.summary)
                        handler = self.event_processor.get_handler(event)
                        if not handler:
                            continue
                        with self.db.begin() as con:
                            handler(con)
                    except:
                        log.exception('Error during event %d:\n%s' % (event['id'], event.dumps(pretty=True)))
                    finally:
                        log_globals.meta = {}

            except IOError as e:
                io_error_count += 1
                log.log(
                    logging.ERROR if io_error_count % 60 == 2 else logging.WARNING,
                    'No connection to Shotgun for ~%d minutes; sleeping for 10s' % (io_error_count / 6),
                    exc_info=True,
                )
                time.sleep(10)

            except:
                # NOTE: The event log may have corrupted its ID tracking, and
                # be in an infinite loop. Only send emails about the first few,
                # because inboxes can fill up.
                error_count += 1
                if error_count <= 10 or error_count % 60 == 1:
                    if error_count >= 10:
                        log.exception('Error %d during event iteration; silencing for ~10 minutes; sleeping for 10s' % error_count)
                    else:
                        log.exception('Error %d during event iteration; sleeping for 10s' % error_count)
                else:
                    log.warning('Error %d during event iteration; sleeping for 10s' % error_count, exc_info=True)
                time.sleep(10)

            else:
                log.warning('EventLog.iter_events_forever() returned; sleeping for 10s')
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
            thread = threading.Thread(target=functools.partial(try_call_except_traceback, self.scan, interval, last_time, auto_last_time, **kwargs))
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




