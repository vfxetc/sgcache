import time
import cProfile as profile

import sqlalchemy as sa

from ..exceptions import EntityMissing, FieldMissing, NoFieldData
from ..path import FieldPath


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

        self.aliased = set()
        self.aliases = {}

        #: A list of expressions to be passed to a SQL ``select(...)``.
        self.select_fields = []
        self.select_state = []

        self.select_from = None
        self.joined = set()

        #: A list of expressions to be passed to ``query.where(...)``.
        self.where_clauses = []
        self.group_by_clauses = []
        self.order_by_clauses = []

        self._start_time = self._last_time = time.time()

    def _debug_time(self, msg):
        now = time.time()
        print '%3dms (+%6dus): %s' % (
            1000 * (now - self._start_time),
            1000000 * (now - self._last_time),
            msg
        )
        self._last_time = now

    def parse_path(self, path):
        """Get a :class:`.FieldPath` for the requested entity type.

        :param str path: The field in a filter or return field.
        :return: The :class:`.FieldPath`.

        """
        return FieldPath(path, self.entity_type_name)

    def get_entity(self, path):
        """Get the :class:`.EntityType` for the tail of a given path.

        :param path: A :class:`.FieldPath` to get the entity for.
        :return: The :class:`.EntityType`.
        :raises: :class:`.EntityMissing` when the requested entity type is not cached;
            allowing this to propigate will result in passing through API3
            requests to the real Shotgun.

        """
        try:
            return self.cache[path[-1][0]]
        except KeyError as e:
            raise EntityMissing(e.args[0])

    def get_field(self, path):
        """Get the :class:`.Field` for the tail of a given path.

        :param path: A :class:`.FieldPath` to get the field for.
        :return: An instance of a subclass of :class:`.Field`
        :raises: :class:`.FieldMissing` when the requested field is not cached;
            allowing this to propigate will result in passing through API3
            requests to the real Shotgun.

        """
        type_ = self.get_entity(path)
        try:
            return type_.fields[path[-1][1]]
        except KeyError as e:
            raise FieldMissing('%s.%s' % (type_.type_name, e.args[0]))

    def get_table(self, path, table=None, include_tail=False):
        """Get an aliased SQLA table for the entity at the tail of a given path.

        The first time a table is requested, it is not aliased. The second time
        it is requested (via a different path) it is aliased to that string path.
        This allows for entity self references via aliases, but for most queries
        to use the native table names.

        This is used by all field classes to get the table to operate on in
        the context of the current operation.

        :param path: A :class:`.FieldPath` to get the table for.
        :return: A SQLA table, potentially aliased.

        """

        # Shortcut association tables.
        if table is not None and table.name not in self.aliases:
            self.aliased.add(table.name)
            self.aliases[table.name] = table
            return table

        name = path.format(head=True, tail=include_tail)
        if name not in self.aliases:
            # we can return the real table the first path it is used from,
            # but after that we must alias it
            if table is None:
                table = self.get_entity(path).table
            if table.name in self.aliased:
                table = table.alias(name)
            self.aliased.add(table.name)
            self.aliases[name] = table
        return self.aliases[name]

    def join(self, table, on):
        """Outer-join the given table onto the query.

        This method is indempotent, and so you need not bother checking
        if you have already joined this table.

        :param table: The table as returned from :meth:`get_table`.
        :param on: SQLA expression of the join predicate.

        """
        if table.name not in self.joined:
            self.select_from = self.select_from.outerjoin(table, on)
            self.joined.add(table.name)

    def prepare_joins(self, path):
        """Prepare all joins that will be required to access the tail of the given path.

        If the given path is a deep-field, all tables along that path must be
        joined into the query in order for the data to be accessed.

        This calls :meth:`.Field.prepare_join` for every deep link in the path.

        :param path: The :class:`FieldPath` to assert is joined.
        :returns: A tuple of the last field, and the state returned from its
            :meth:`~.Field.prepare_join` to be passed to its
            :meth:`~.Field.check_for_join`.

        """

        field = state = None

        for i in xrange(0, len(path) - 1):
            field_path = path[:i+1]
            field = self.get_field(field_path)
            state = field.prepare_join(self, field_path, path[:i+2])

        # We only need to track the last join to check if it was successful,
        # since the previous ones are a requirement of it
        return field, state

    def check_for_joins(self, row, state_tuple):
        """Check if the joins setup by :meth:`prepare_joins` succeeded.

        Used to filter out deep-fields that did not match.

        :param row: SQLA result row.
        :param state_tuple: Return value from :meth:`prepare_joins`.
        :returns bool: true if the join occurred.

        """
        field, state = state_tuple
        if field is not None:
            return field.check_for_join(self, row, state)
        else:
            return True

    def prepare_filters(self, filters):
        """Convert a set of Shotgun filters into a SQLA expression.

        :param filters: A backend-style Shotgun filter dict.
        :return: A SQLA expression, passable to ``query.where(...)``.

        """

        clauses = []
        for filter_ in filters['conditions']:

            if 'conditions' in filter_:
                clause = self.prepare_filters(filter_)
            else:

                raw_path = filter_['path']
                relation = filter_['relation']
                values = filter_['values']

                path = self.parse_path(raw_path)
                self.prepare_joins(path) # make sure it is availible

                field = self.get_field(path)
                clause = field.prepare_filter(self, path, relation, values)

            if clause is not None:
                clauses.append(clause)

        if clauses:
            return (sa.and_ if filters['logical_operator'] == 'and' else sa.or_)(*clauses)


    def prepare(self):
        """Prepare the entire SQLA query.

        This method is *not* indempodent, and mutates the operation.

        :returns: The SQLA query.

        """

        # Hacky use of FieldPath here...
        self.select_from = self.get_table(FieldPath([(self.entity_type_name, None)]))

        self.where_clauses.append(self.select_from.c._active == self.return_active)

        self.return_fields.append('id')

        for raw_path in self.return_fields:

            path = self.parse_path(raw_path)
            join_state = self.prepare_joins(path) # make sure it is availible

            field = self.get_field(path)
            state = field.prepare_select(self, path)

            self.select_state.append((path, join_state, field, state))

        clause = self.prepare_filters(self.filters)
        if clause is not None:
            self.where_clauses.append(clause)

        for sort_spec in self.sorts:
            path = self.parse_path(sort_spec['field_name'])
            self.prepare_joins(path)
            field = self.get_field(path)
            sort_expr = field.prepare_order(self, path)
            if sort_spec.get('direction') == 'desc':
                sort_expr = sort_expr.desc()
            self.order_by_clauses.append(sort_expr)

        query = sa.select(self.select_fields, use_labels=True).select_from(self.select_from)

        if self.where_clauses:
            query = query.where(sa.and_(*self.where_clauses))
        if self.order_by_clauses:
            query = query.order_by(*self.order_by_clauses)
        if self.group_by_clauses:
            query = query.group_by(*self.group_by_clauses)
        if self.offset:
            query = query.offset(self.offset)
        if self.limit:
            query = query.limit(self.limit)

        return query

    def extract(self, res):
        """Extract entities from a SQLA row iterator.

        Uses :meth:`.Field.extract_select` for each field.

        :param res: The SQLA result iterator.
        :returns: list of entity dicts.

        """

        rows = []
        for raw_row in res:
            row = {'type': self.entity_type_name}
            for path, join_state, field, state in self.select_state:
                if not self.check_for_joins(raw_row, join_state):
                    continue
                try:
                    value = field.extract_select(self, raw_row, state)
                except NoFieldData:
                    pass
                else:
                    row[path.format()] = value
            rows.append(row)
        return rows

    def run(self, cache):
        """Run the operation.

        :param cache: The :class:`.Cache`.
        :returns: API3 compatible results.

        """

        self.cache = cache
        self.entity_type = cache[self.entity_type_name]

        query = self.prepare()

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

        #self._debug_time('executed query')

        if False:
            profiler = profile.Profile()
            entities = profiler.runcall(self.extract, db_res)
            profiler.print_stats()
        else:
            entities = self.extract(db_res)

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
