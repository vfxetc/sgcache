import contextlib
import datetime
import logging
import os
import re
import traceback


try:
    import sgapi
except ImportError as e:
    sgapi = None
try:
    import shotgun_api3
except ImportError as e:
    shotgun_api3 = None

try:
    import shotgun_api3_registry
except ImportError:
    shotgun_api3_registry = None



def get_shotgun_class(provider=None, strict=True):

    if provider:

        try:
            module = {
                'sgapi': sgapi,
                'shotgun_api3': shotgun_api3,
            }[provider]
        except KeyError:
            raise ValueError("%s is not a Shotgun api type")

        if module:
            return module.Shotgun
        elif strict:
            raise RuntimeError("%s is not installed" % provider)

    if shotgun_api3:
        return shotgun_api3.Shotgun
    elif sgapi:
        return sgapi.Shotgun
    else:
        raise RuntimeError("no Shotgun APIs installed")


def get_shotgun_kwargs(config=None):

    if config and config.SHOTGUN_URL:
        return {
            'base_url': config.SHOTGUN_URL,
            'script_name': config.SHOTGUN_SCRIPT_NAME,
            'api_key': config.SHOTGUN_API_KEY,
        }

    elif shotgun_api3_registry:
        # In Western Post, this envvar signals to return the cache. That would
        # make very little sense here.
        os.environ.pop('SGCACHE', None)
        return shotgun_api3_registry.get_kwargs()

    else:
        raise RuntimeError('please set SHOTGUN_URL, or provide shotgun_api3_registry.get_kwargs')


def get_shotgun(*args, **kwargs):
    config = kwargs.pop('config', None)
    return get_shotgun_class(*args, **kwargs)(**get_shotgun_kwargs(config))


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


def try_call_except_traceback(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except:
        traceback.print_exc()
        raise
