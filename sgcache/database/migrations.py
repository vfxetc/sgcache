import functools


_migrations = []
def patch(func=None, name=None):
    if func is None:
        return functools.partial(patch, name=name)

    name = name or func.__name__
    name = name.strip('_')
    _migrations.append((name, func))

    return func

