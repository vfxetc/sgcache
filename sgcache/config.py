'''Default config goes here.'''
import os



SQLA_URL = 'sqlite://'
SQLA_ECHO = False

SCHEMA = 'schema/keystone-basic.yml'

CLEAR_LOGGERS = True

WATCH_EVENTS = True
AUTO_LAST_ID = False


# Override with SGCACHE_* envvars.
for k, v in os.environ.iteritems():
    if k.startswith('SGCACHE_'):
        globals()[k[8:]] = v
