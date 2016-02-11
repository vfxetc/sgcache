
import argparse
import ast
import logging
import os
import copy
import re
import collections


# Sentinel for default values lower down.
NotSet = object()


ConfigSpec = collections.namedtuple('ConfigSpec', 'name default sections doc arg_kwargs')

class Config(dict):

    specifications = []

    @classmethod
    def register(cls, name, default, sections=None, doc=None, arg_kwargs=None):
        cls.specifications.append(ConfigSpec(name, default, sections or (), doc, arg_kwargs))

    def __init__(self):
        super(Config, self).__init__()
        for spec in self.specifications:
            self[spec[0]] = spec[1]
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

    def add_arguments(self, parser, sections=None):

        sections = set(sections or ())

        group_name = None
        group = None

        for spec in self.specifications:

            k = spec.name
            if not k.isupper(): # Extra protection.
                continue

            # Only if it is in requested sections
            if sections and not sections.intersection(spec.sections):
                continue

            group_names = [s for s in spec.sections if s in sections or not sections]
            if group_name not in group_names:
                group_name = group_names[0]
                group = parser.add_argument_group(group_name.title() + ' Options')

            kwargs = dict(spec.arg_kwargs or {})
            flags = kwargs.pop('flags', ['--' + k.lower().replace('_', '-')])
            kwargs['dest'] = 'config_' + k
            if kwargs.get('action') not in ('store_true', ):
                kwargs.setdefault('metavar', k)
            kwargs.setdefault('default', NotSet)
            group.add_argument(*flags, **kwargs)

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





Config.register('SHOTGUN_URL', None, ['shotgun'], '''
    Base URL of the Shotgun server. If this is not set, we will use the follwing
    code to get arguments::

        import shotgun_api3_registry
        sg = Shotgun(*shotgun_api3_registry.get_args())
''')
Config.register('SHOTGUN_SCRIPT_NAME', None, ['shotgun'], '''
    Script name for Shotgun server.
''')
Config.register('SHOTGUN_API_KEY', None, ['shotgun'], '''
    API key for Shotgun server.
''')

Config.register('SQLA_URL', 'sqlite:///%s' % os.path.abspath(os.path.join(__file__, '..', '..', 'var', 'data.db')), ['core'], '''
    SQLAlchemy url for the primary data store. Default uses SQLite, but Postgresql is
    highly recommended for production use::

        postgres:///sgcache
''')

Config.register('SCHEMA', 'schema/default-basic.yml', ['core'], '''
    The relative path to the schema file to use.
''')


Config.register('WATCH_EVENTS', True, ['daemon'], '''
    Should we watch :ref:`the event log <event_log>` for changes? This is
    generally required to stay in sync with Shotgun.
''')

Config.register('SCAN_CHANGES', True, ['daemon'], '''
    Should we :ref:`periodically scan <periodic_scans>` for changed entities?
    This is a secondary method of staying in sync, designed to catch any data
    that the event watcher may have missed.
''')

Config.register('WATCH_IDLE_DELAY', 5.0, ['events', 'daemon'], '''
    Delay (in seconds) between polls of :ref:`the event log <event_log>`.
''')


Config.register('SCAN_INTERVAL', 300, ['scanner'], '''
    Delay (in seconds) between :ref:`scans <periodic_scans>` of changed entities.
''')
Config.register('SCAN_SINCE', 3600, ['scanner'], '''
    How far back to :ref:`scan <periodic_scans>` (in seconds) on initial scan;
    subsequent scans will only scan for changes since the previous scan.

    .. warning:: Setting this to a falsy value will result in a complete scan
                 of your Shotgun server.
''')
Config.register('SCAN_TYPES', [], ['scanner'], '''
    Which entity types should be scanned? Falsy values default to all types.
    Delimit with commas in the command-line.
''', arg_kwargs=dict(
    type=lambda x: [y.strip() for y in x.split(',')]
))
Config.register('SCAN_PROJECTS', [], ['scanner'], '''
    Which projects (by ID) should be scanned? Empty values default to all projects.
    Delimit with commas in the command-line.
''', arg_kwargs=dict(
    type=lambda x: [int(y.strip()) for y in x.split(',')]
))

Config.register('AUTO_LAST_ID', False, ['scanner', 'events'], '''
    Should we automatically detect when the last time the cache was updated?
    This affects the start location of both the event log and scanner
    (overriding :attr:`SCAN_SINCE`).
''')


# === WEB ===

Config.register('PORT', int(os.environ.get('PORT', 8010)), ['web', 'daemon'], '''
    The port of the web server for the API proxy; set to something falsey to
    disable the web server entirely. Also set via ``$PORT`` envvar.
''')

Config.register('GUNICORN_WORKERS', 4, ['web'], '''
    Number of web workers.
''')

Config.register('GUNICORN_WORKER_CLASS', 'gevent', ['web'], '''
    Class used for driving web workers.
''')

Config.register('MAX_CONTENT_LENGTH', '1024**3', ['web'])


# === LOGGING ===

Config.register('SQLA_ECHO', False, ['logging'], '''
    Should SQLA engines log everything they do? Useful for development and debugging.
''')
Config.register('LOGGING_FILE_DIR', None, ['logging'], '''
    Directory for log files, relative to :attr:`.DATA_ROOT`
''')
Config.register('LOGGING_FILE_LEVEL', logging.INFO, ['logging'], '''
    Python logging level to capture into files; default os ``logging.INFO``.
''')
Config.register('LOGGING_SMTP_ARGS', None, ['logging'], '''
    SMPT settings for emailing error logs; is a tuple of arguments for a
    :class:`logging.handlers.SMTPHandler`::

        ('mail.westernx', 'sgevents@mail.westernx', ['mboers@mail.westernx'], 'SGCache Log Event')
''')
Config.register('LOGGING_SMTP_LEVEL', logging.ERROR, ['logging'], '''
    Python logging level to email; default is ``logging.ERROR``.
''')
Config.register('CLEAR_LOGGERS', True, ['logging'], '''
    Should existing handlers be cleared from the root of Python's logging system?
    Useful if you have site-wide capture of Python logging that you don't want
    to pollute with the minutia of the cache.
''')


# === OTHER ===

Config.register('CONFIG', None, ['environ'], '''
    List of external configration files to include; usually set via $SGCACHE_CONFIG
    as a colon-delimited list.
''', arg_kwargs=dict(
    metavar='PATH',
    help='Path to config.py file',
))

Config.register('TESTING', False, ['core'], '''
    Allows for unsafe behaviour for unit testing.
''', arg_kwargs=dict(
    action='store_true',
))

Config.register('DATA_ROOT', os.path.abspath(os.path.join(__file__, '..', '..', 'var')), ['core'], '''
    Where runtime data (logs, sockets, locks, etc..) is stored.
''')


if os.environ.get('IS_SPHINX'):
    # Build up the docstring.
    doc_parts = []
    last_heading = None
    for spec in Config.specifications:
        if spec.sections and last_heading != spec.sections[0]:
            last_heading = spec.sections[0]
            doc_parts.append('%s\n%s\n' % (last_heading.title(), '-' * len(last_heading)))
        doc_parts.append('.. data:: %s\n\n%s' % (spec.name, spec.doc))
    __doc__ = '\n\n'.join(doc_parts)
