import argparse
import ast
import logging
import os
import copy
import re

NotSet = object()

defaults = dict(

    # Flask config.
    MAX_CONTENT_LENGTH = 1024**3, # 1GB; must match nginx.

    #: Base URL of the Shotgun server. If this is not set, we will use the follwing
    #: code to get arguments::
    #:
    #:     import shotgun_api3_registry
    #:     sg = Shotgun(*shotgun_api3_registry.get_args())
    SHOTGUN_URL = None,

    #: Script name for Shotgun server.
    SHOTGUN_SCRIPT_NAME = None,

    #: API key for Shotgun server.
    SHOTGUN_API_KEY = None,


    #: SQLAlchemy url for the primary data store. Default uses SQLite, but Postgresql is
    #: highly recommended for production use::
    #:
    #:     postgres:///sgcache
    SQLA_URL = 'sqlite:///%s' % os.path.abspath(os.path.join(__file__, '..', '..', 'var', 'data.db')),

    #: Should SQLA engines log everything they do? Useful for development and debugging.
    SQLA_ECHO = False,


    #: The relative path to the schema file to use.
    SCHEMA = 'schema/keystone-basic.yml',


    #: Should existing handlers be cleared from the root of Python's logging system?
    #: Useful if you have site-wide capture of Python logging that you don't want
    #: to pollute with the minutia of the cache.
    CLEAR_LOGGERS = True,


    #: Should we watch :ref:`the event log <event_log>` for changes? This is
    #: generally required to stay in sync with Shotgun.
    WATCH_EVENTS = True,

    #: Delay (in seconds) between polls of :ref:`the event log <event_log>`.
    WATCH_IDLE_DELAY = 5.0,


    #: Should we :ref:`periodically scan <periodic_scans>` for changed entities?
    #: This is a secondary method of staying in sync, designed to catch any data
    #: that the event watcher may have missed.
    SCAN_CHANGES = True,

    #: Delay (in seconds) between :ref:`scans <periodic_scans>` of changed entities.
    SCAN_INTERVAL = 5 * 60,

    #: How far back to :ref:`scan <periodic_scans>` (in seconds) on initial scan;
    #: subsequent scans will only scan for changes since the previous scan.
    #:
    #: .. warning:: Setting this to a falsy value will result in a complete scan
    #:              of your Shotgun server.
    SCAN_SINCE = 60 * 60,


    #: Should we automatically detect when the last time the cache was updated?
    #: This affects the start location of both the event log and scanner
    #: (overriding :attr:`SCAN_SINCE`).
    AUTO_LAST_ID = False,


    #: The port of the web server for the API proxy; set to something falsey to
    #: disable the web server entirely. Also set via ``$PORT`` envvar.
    PORT = int(os.environ.get('PORT', 8010)),


    #: Number of web workers.
    GUNICORN_WORKERS = 4,

    #: Class used for driving web workers.
    GUNICORN_WORKER_CLASS = 'gevent',


    #: Directory for log files; defaults to ``var/log`` of the installation.
    LOGGING_FILE_DIR = os.path.abspath(os.path.join(__file__, '..', '..', 'var', 'log')),

    #: Python logging level to capture into files; default os ``logging.INFO``.
    LOGGING_FILE_LEVEL = logging.INFO,

    #: SMPT settings for emailing error logs; is a tuple of arguments for a
    #: :class:`logging.handlers.SMTPHandler`::
    #:
    #:     ('mail.westernx', 'sgevents@mail.westernx', ['mboers@mail.westernx'], 'SGCache Log Event')
    LOGGING_SMTP_ARGS = None,

    #: Python logging level to email; default is ``logging.ERROR``.
    LOGGING_SMTP_LEVEL = logging.ERROR,


    #: List of external configration files to include; usually set via $SGCACHE_CONFIG
    #: as a colon-delimited list.
    CONFIG = None,

)


class Config(dict):

    def __init__(self):
        super(Config, self).__init__()
        self.update(copy.deepcopy(defaults))
        self.update_from_environ()
        self.update_from_includes()

    def __getattr__(self, name):
        if not name.isupper():
            raise AttributeError(name)
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.isupper():
            self[name] = value
        else:
            super(Config, self).__setattr__(name, value)

    def update_from_environ(self):
        # Override with SGCACHE_* envvars. We attempt to parse them as Python literals,
        # so that `SGCACHE_PORT=9000` results in the integer 9000 instead of a string.
        for k, v in os.environ.iteritems():
            if k.startswith('SGCACHE_'):
                try:
                    v = ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    pass
                self[k[8:]] = v

    def update_from_includes(self):
        paths = self.CONFIG
        if isinstance(paths, basestring):
            paths = filter(None, paths.split(':'))
        if paths:
            for path in paths:
                execfile(path, self)

    def add_arguments(self, parser):
        for k in defaults:
            if not k.isupper(): # Extra protection.
                continue
            parser.add_argument('--' + k.lower().replace('_', '-'), dest='config_' + k, default=NotSet)

    def parse_args(self, args):
        for name, value in args.__dict__.iteritems():

            if value is NotSet:
                continue

            m = re.match(r'^config_([A-Z_]+)$', name)
            if not m:
                continue
            key = m.group(1)

            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                pass

            self[key] = value

    def update_from_argv(self, argv=None):
        """Updates the configuration from command-line arguments.

        All options are presented as double-hyphened options, and require a value.
        Those values will be parsed as Python literals if possible. Falsy values
        may therefore be ``False``, ``0``, or ``""``.

        Example::

            python -m sgcache --port 9000 --auto-last-id True

        :param argv: List of arguments to use; ``None`` implies ``sys.argv[1:]``.

        .. warning:: This directly mutates the ``sgcache.config`` module globals.

        """
        parser = argparse.ArgumentParser()
        self.add_arguments(parser)
        args = parser.parse_known_args()
        self.parse_args(args)


