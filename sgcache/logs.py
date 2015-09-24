from urllib import quote
import datetime
import itertools
import logging
import os
import sys
import threading
import time

try:
    from flask import request
except ImportError:
    request = None


log_globals = threading.local()


def setup_logs(app=None):

    request_counter = itertools.count(1)
    http_access_logger = logging.getLogger('http.access')

    if app:

        @app.before_request
        def prepare_for_injection():
            log_globals.http_start_time = time.time()
            log_globals.meta = {
                'request': next(request_counter),
                'ip': request.access_route[-1] if request.access_route else request.remote_addr,
            }

        @app.after_request
        def log_request(response):

            if not getattr(log_globals, 'skip_http_log', False):
                http_access_logger.info('%(method)s %(path)s -> %(status)s in %(duration).1fms' % {
                    'method': request.method,
                    'path': quote(request.path.encode('utf8')),
                    'status': response.status_code,
                    'duration': 1000 * (time.time() - log_globals.http_start_time),
                })

            return response

    # Silence requests
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if app and app.debug else logging.INFO)

    # Clear existing handlers.
    root.handlers[:] = []

    # Disable SQLAlchemy's extra logging handlers
    logging.getLogger('sqlalchemy.engine.base.Engine').handlers[:] = []

    # Disable Werkzeug's logger.
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    injector = RequestContextInjector()
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s pid:%(pid)d %(meta_str)s %(name)s - %(message)s')

    def add_handler(handler):
        handler.addFilter(injector)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Console logging.
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG if app and app.debug else logging.INFO)
    add_handler(handler)

    # File logging.
    if app and app.config['LOGGING_FILE_DIR']:
        if not os.path.exists(app.config['LOGGING_FILE_DIR']):
            os.makedirs(app.config['LOGGING_FILE_DIR'])
        handler = PatternedFileHandler(os.path.join(app.config['LOGGING_FILE_DIR'], '{date}.{pid}.log'))
        handler.setLevel(app.config['LOGGING_FILE_LEVEL'])
        add_handler(handler)

    # Email logging.
    if app and app.config['LOGGING_SMTP_ARGS']:
        handler = logging.handlers.SMTPHandler(*app.config['LOGGING_SMTP_ARGS'])
        handler.setLevel(app.config['LOGGING_SMTP_LEVEL'])
        add_handler(handler)



class RequestContextInjector(logging.Filter):

    def filter(self, record):
        record.pid = os.getpid() # Would love to cache this, but we can't.
        record.__dict__.update(log_globals.__dict__)

        meta = getattr(record, 'meta', {})
        record.meta_str = ' '.join('%s:%s' % x for x in sorted(meta.iteritems()))
        return True


class PatternedFileHandler(logging.FileHandler):

    def __init__(self, *args, **kwargs):
        self._last_path = None
        super(PatternedFileHandler, self).__init__(*args, **kwargs)

    def _current_path(self):
        now = datetime.datetime.utcnow()
        return self.baseFilename.format(
            date=now.date().isoformat(),
            pid=os.getpid(),
        )

    def _open(self):
        self._last_path = path = self._current_path()
        return open(path, self.mode)

    def emit(self, record):
        if self._last_path and self._last_path != self._current_path():
            self.close()
        super(PatternedFileHandler, self).emit(record)


