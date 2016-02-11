import datetime
import itertools
import logging
import re
import sys
import time

from .logs import log_globals
from .utils import parse_interval, get_shotgun


log = logging.getLogger(__name__)


class Scanner(object):

    def __init__(self, schema, last_time=None, types=None, projects=None, config=None):

        self.schema = schema
        self.last_time = parse_interval(last_time) if isinstance(last_time, basestring) else last_time
        self.types = types
        self.projects = projects

        self._log_counter = itertools.count(1)
        self.shotgun = get_shotgun('sgapi', config=config)

    def scan(self, interval=None):

        interval = parse_interval(interval) if interval else None

        sleep_target = time.time()

        while True:

            log_globals.meta = {'scan': next(self._log_counter)}

            scan_start = datetime.datetime.utcnow() # would be great if this matched the sleep target
            self._scan()
            self.last_time = scan_start

            if not interval:
                break

            # Figure out the next time
            while sleep_target < time.time():
                sleep_target += interval
            delay = sleep_target - time.time()
            log.info('sleeping %ds until next scan' % delay)
            time.sleep(delay)

    def _scan(self):

        base_filters = []
        if self.last_time:
            if isinstance(self.last_time, (int, float)):
                self.last_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.last_time)
            base_filters.append(('updated_at', 'greater_than', self.last_time))

        log.info('scan starting')
        counts = {}

        for entity_type in sorted(self.schema._entity_types.itervalues(), key=lambda e: e.type_name):

            if self.types and entity_type.type_name not in self.types:
                continue

            #log.info('scanning %ss' % entity_type.type_name)

            filters = base_filters[:]

            if self.projects and entity_type.type_name not in ('ApiUser', 'HumanUser'):
                # Need to make sure the project field actually exists.
                project_field = entity_type.fields['project']
                if project_field and project_field.is_cached():
                    filters.append(('project', 'in', [{'type': 'Project', 'id': pid} for pid in self.projects]))

            return_fields = sorted(name for name, field in entity_type.fields.iteritems() if field.is_cached())

            for entity in self._find_active_and_retired(entity_type.type_name, filters, return_fields, threads=1, per_page=100):

                for key in return_fields:
                    value = entity.get(key)
                    if isinstance(value, datetime.datetime):
                        entity[key] = value.isoformat() + 'Z'

                log.info('updating %s %s %d%s' % (
                    'active' if entity['_active'] else 'retired',
                    entity['type'],
                    entity['id'],
                    ' "%s"' % entity['name'][:40] if entity.get('name') else ''
                ))

                self.schema.create_or_update(entity.pop('type'), entity, create_with_id=True)
                counts[entity_type.type_name] = counts.get(entity_type.type_name, 0) + 1

        summary = ', '.join('%d %ss' % (count, name) for name, count in sorted(counts.iteritems()) if count)
        log.info('scan completed; updated %s' % (summary or 'nothing'))

    def _find_active_and_retired(self, *args, **kwargs):
        for active in True, False:
            kwargs['retired_only'] = not active
            for e in self.shotgun.find(*args, **kwargs):
                e['_active'] = active
                yield e
