import time
import cProfile as profile

import sqlalchemy as sa

from ..exceptions import EntityMissing, FieldMissing, NoFieldData
from ..path import FieldPath
from ..select import SelectBuilder

class Api3ReadOperation(object):

    """Operation to process an API3-style "read" request.

    :param dict request: The request itself with:

        - ``type``
        - ``filters``
        - ``return_fields``
        - ``paging.entities_per_page``
        - ``paging.current_page``
        - ``sorts``
        - ``return_only``

    """

    def __init__(self, request):

        self.request = request

        self.entity_type_name = request['type']
        self.filters = request['filters']
        self.return_fields = request['return_fields']
        self.limit = request['paging']['entities_per_page']
        self.offset = self.limit * (request['paging']['current_page'] - 1)
        self.sorts = request.get('sorts', [])
        self.return_active = request.get('return_only') != 'retired'

        self._start_time = self._last_time = time.time()

    def _debug_time(self, msg):
        now = time.time()
        print '%3dms (+%6dus): %s' % (
            1000 * (now - self._start_time),
            1000000 * (now - self._last_time),
            msg
        )
        self._last_time = now

    def run(self, cache):
        """Run the operation.

        :param cache: The :class:`.Cache`.
        :returns: API3 compatible results.

        """

        selector = SelectBuilder(cache, self.entity_type_name)
        selector.return_active = self.return_active
        selector.add_return_field('id')
        for field in self.return_fields:
            selector.add_return_field(field)
        selector.add_api3_filters(self.filters)
        selector.add_api3_sorts(self.sorts)
        query = selector.finalize()

        # print '========'
        # print str(query)
        # print '--------'

        if self.offset:
            query = query.offset(self.offset)
        if self.limit:
            query = query.limit(self.limit)

        #self._debug_time('prepared query')

        if False:
            try:
                sql = str(query.compile(cache.db, compile_kwargs={"literal_binds": True}))
                explain_res = cache.db.execute('EXPLAIN ANALYZE ' + sql)
                print sql
                print
                for row in explain_res:
                    print row[0]
                print '========='
            except Exception as e:
                print 'EXPLAIN FAILED:', e


        db_res = cache.db.execute(query)
        entity_iter = selector.extract(db_res)

        #self._debug_time('executed query')

        if False:
            profiler = profile.Profile()
            entities = profiler.runcall(list, entity_iter)
            profiler.print_stats()
        else:
            entities = list(entity_iter)

        #self._debug_time('extracted results')

        # paging_info.entity_count represents the total entities that would
        # be returned if there was no paging applied. Since the shotgun_api3
        # does not care about the specific value, only if it signals that there
        # *might* be more data to grab, we fake it for now.
        entity_count = self.offset + len(entities)
        if len(entities) == self.limit:
            # fake that there is more than one full page left.
            entity_count += self.limit + 1

        return {
            'entities': entities,
            'paging_info': {
                'entity_count': entity_count,
            },
        }
