import contextlib
import logging


@contextlib.contextmanager
def log_exceptions(log, msg=None):
    try:
        yield
    except:
        log = logging.getLogger(log) if isinstance(log, basestring) else log
        log.exception(msg or 'uncaught exception')


def iter_unique(source, key=None):
    """Iter unique values of the given source, in order.

    :param key: Function deriving the key for each object.

    """
    seen = set()
    for x in source:
        k = key(x) if key else x
        if k in seen:
            continue
        seen.add(k)
        yield x
