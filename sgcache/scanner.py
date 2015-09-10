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

    def __init__(self, schema, last_time=None, types=None, projects=None):

        self.schema = schema
        self.last_time = parse_interval(last_time) if isinstance(last_time, basestring) else last_time
        self.types = types
        self.projects = projects

        self._log_counter = itertools.count(1)
        self.shotgun = get_shotgun('sgapi')

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
            if self.projects and 'project' in entity_type.fields and entity_type.type_name not in ('ApiUser', 'HumanUser'):
                filters.append(('project', 'in', [{'type': 'Project', 'id': pid} for pid in self.projects]))

            return_fields = sorted(name for name, field in entity_type.fields.iteritems() if field.include_in_scan())

            for entity in self._find_active_and_retired(entity_type.type_name, filters, return_fields, threads=1, per_page=100):

                for key in return_fields:
                    value = entity[key]
                    if isinstance(value, datetime.datetime):
                        entity[key] = v.isoformat() + 'Z'

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









if __name__ == '__main__':

    import argparse

    import sqlalchemy as sa
    import yaml

    from . import config
    from .logs import setup_logs
    from .cache import Cache
    from .schema import Schema

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--interval', type=parse_interval)
    parser.add_argument('-t', '--type', action='append')
    parser.add_argument('-p', '--project', type=int, action='append')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--last-id', type=int)
    group.add_argument('--last-time', type=parse_interval)
    group.add_argument('--full', action='store_true')

    args = parser.parse_args()

    if args.last_id:
        print >> sys.stderr, '--last-id is not supported yet'
        exit(1)
    if not args.last_time and not args.full:
        print >> sys.stderr, '--last-time or --full is required'
        exit(1)



    db = sa.create_engine(config.SQLA_URL, echo=bool(config.SQLA_ECHO))

    # Setup logging *after* SQLA so that it can deal with its handlers.
    setup_logs()

    schema = Schema.from_yaml(config.SCHEMA)
    cache = Cache(db, schema)

    cache.scan(interval=args.interval, last_time=args.last_time, types=args.type, projects=args.project)

