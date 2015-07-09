import contextlib
import logging


@contextlib.contextmanager
def log_exceptions(log, msg=None):
    try:
        yield
    except:
        log = logging.getLogger(log) if isinstance(log, basestring) else log
        log.exception(msg or 'uncaught exception')
