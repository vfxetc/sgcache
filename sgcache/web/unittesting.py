import functools

from .core import api3_method
from ..exceptions import Fault

import sqlalchemy as sa
from flask import current_app, g


def testing_only(func):
    @functools.wraps(func)
    def _testing_only(api3_request):
        cache = current_app.cache
        if not cache.config['TESTING']:
            raise Fault('%s only works when testing' % func.__name__, 1001)
        return func(api3_request)
    return _testing_only


@api3_method
@testing_only
def clear(api3_request):
    current_app.cache._clear()


@api3_method
@testing_only
def count(api3_request):
    res = {}
    cache = current_app.cache
    with cache.db_begin() as con:
        for type_name, entity_type in current_app.cache.iteritems():
            cur = con.execute(sa.select([sa.func.count(entity_type.table.c.id)]))
            row = cur.fetchone()
            if row[0]:
                res[type_name] = row[0]
    return res
