'''Default config goes here.'''
import argparse
import os


SQLA_URL = 'sqlite://'
SQLA_ECHO = False

SCHEMA = 'schema/keystone-basic.yml'

CLEAR_LOGGERS = True

WATCH_EVENTS = False
AUTO_LAST_ID = False

SCAN_INTERVAL = None
SCAN_SINCE = None

PORT = 8010


# Override with SGCACHE_* envvars.
for k, v in os.environ.iteritems():
    if k.startswith('SGCACHE_'):
        globals()[k[8:]] = v


def update_from_argv():

    parser = argparse.ArgumentParser()

    notset = object()
    for k in globals():
        if not k.isupper():
            continue
        parser.add_argument('--' + k.lower().replace('_', '-'), default=notset)

    args = parser.parse_args()

    for k, v in args.__dict__.iteritems():
        if v is not notset:
            globals()[k.upper()] = v

