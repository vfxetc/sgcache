import itertools
import logging
import os
import sys
import threading
import time
from urllib import quote

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
                'ip': request.remote_addr,
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

    add_handler(logging.StreamHandler(sys.stderr))




class RequestContextInjector(logging.Filter):

    static = {
        'pid': os.getpid(),
    }

    def filter(self, record):
        record.__dict__.update(self.static)
        record.__dict__.update(log_globals.__dict__)

        meta = getattr(record, 'meta', {})
        record.meta_str = ' '.join('%s:%s' % x for x in sorted(meta.iteritems()))
        return True

