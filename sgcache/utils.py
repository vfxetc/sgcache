import contextlib
import datetime
import logging
import re


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


def parse_interval(interval):
    
    if isinstance(interval, (int, float)):
        return interval

    m = re.match(r'''^(\d+)(
        s(ec(ond)?)?s? |
        m(in(ute)?)?s? |
        h(ou)?r?s? |
        d(ay)?s? |
        w(eek)?s? |
        y(ear)?s?
    )?$''', interval.strip(), re.VERBOSE)
    if not m:
        raise ValueError('bad interval: %r' % interval)

    number, unit = m.group(1, 2)
    
    unit = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks',
    }[unit[0] if unit else 's']

    delta = datetime.timedelta(**{unit: int(number)})
    return delta.total_seconds()


        