import contextlib
import datetime
import logging
import re


from . import config

try:
    import shotgun_api3_registry
except ImportError:
    shotgun_api3_registry


def get_shotgun_args():
    if config.SHOTGUN_URL:
        return (config.SHOTGUN_URL, config.SHOTGUN_SCRIPT_NAME, config.SHOTGUN_API_KEY)
    elif shotgun_api3_registry:
        return shotgun_api3_registry.get_args()
    else:
        raise RuntimeError('please set SHOTGUN_URL, or provide shotgun_api3_registry.get_args')


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


        