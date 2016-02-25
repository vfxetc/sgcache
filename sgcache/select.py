import time
import cProfile as profile

import sqlalchemy as sa

from .exceptions import EntityMissing, FieldMissing, NoFieldData, Fault
from .path import FieldPath


class SelectBuilder(object):

    """Assistant to create select queries, and then interpret their results."""

    def __init__(self, cache, entity_type_name, return_active=True, root=None):

        self.cache = cache
        self.entity_type_name = entity_type_name
        self.return_active = return_active

        self._root_builder = root or self
        self._subquery_count = 0
        if root:
            root._subquery_count += 1
            self._subquery_id = root._subquery_count
        else:
            self._subquery_id = 0

        # To keep track of what tables have already been aliased.
        self.aliases = {}

        #: A list of expressions to be passed to a SQL ``select(...)``.
        self.select_fields = []
        self.select_state = []

        # Hacky use of FieldPath here...
        self.base_table = self.get_table(FieldPath([(self.entity_type_name, None)]))
        self.select_from = self.base_table

        #: A set of table/alias names that have already been joined into :attr:`.select_from`.
        self.joined = set()

        #: A list of expressions to be passed to ``query.where(...)``.
        self.where_clauses = []
        self.group_by_clauses = []
        self.order_by_clauses = []

    def subquery(self, path):
        return self.__class__(self.cache, path[-1][0], root=self)

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

        # if table is not None: # For association tables.
            # name = table.name
        # else:
        name = path.format(head=True, tail=include_tail)
        must_alias = False

        # Namespace subqueries.
        if self._subquery_id:
            name = 'sub%d_%s' % (self._subquery_id, name)
            must_alias = True

        if name not in self.aliases:
            # We can usually return the real table the first path it is used from,
            # but after that we must alias it.
            if table is None:
                table = self.get_entity(path).table
            if must_alias or table.name in self.aliases:
                table = table.alias(name)
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

    def prepare_api3_filters(self, filters):
        """Convert a set of Shotgun filters into a SQLA expression.

        :param filters: A backend-style Shotgun filter dict.
        :return: A SQLA expression, passable to ``query.where(...)``.

        """

        clauses = []
        for filter_ in filters['conditions']:

            if 'conditions' in filter_:
                clause = self.prepare_api3_filters(filter_)
                clauses.append(clause)
                continue

            raw_path = filter_['path']
            relation = filter_['relation']
            values = filter_['values']

            path = self.parse_path(raw_path)
            for i in xrange(0, len(path) - 1):

                join_path = path[:i+1]
                next_path = path[:i+2]
                field = self.get_field(join_path)

                # Multi-entity fields take over the filtering process
                clause = field.prepare_deep_filter(self, join_path, next_path, path, relation, values)
                if clause is not None:
                    break

                # Join through everything else; we don't care about the
                # state returned from here.
                state = field.prepare_join(self, join_path, next_path)
                if state is None:
                    raise Fault('cannot join through %s' % join_path.format())

            else:
                field = self.get_field(path)
                clause = field.prepare_filter(self, path, relation, values)

            if clause is None:
                raise Fault('cannot filter %s' % path.format())
            clauses.append(clause)

        if clauses:
            return (sa.and_ if filters['logical_operator'] == 'and' else sa.or_)(*clauses)

    def join_to_path(self, path):
        join_state = join_field = None
        for i in xrange(0, len(path) - 1):
            join_path = path[:i+1]
            join_field = self.get_field(join_path)
            join_state = join_field.prepare_join(self, join_path, path[:i+2])
            if join_state is None:
                raise Fault('cannot join through %s' % join_path.format())
        return join_field, join_state

    def add_return_field(self, path):
        if isinstance(path, basestring):
            path = self.parse_path(path)

        try:
            join_field, join_state = self.join_to_path(path)
        except Fault:
            return

        field = self.get_field(path)
        state = field.prepare_select(self, path)
        self.select_state.append((path, join_field, join_state, field, state))

    def add_api3_filters(self, filters):
        clause = self.prepare_api3_filters(filters)
        if clause is not None:
            self.where_clauses.append(clause)

    def add_api3_sorts(self, sorts):
        for spec in sorts:
            self.add_sort(spec['field_name'], spec.get('direction') == 'desc')

    def add_sort(self, path, desc=False):
        if isinstance(path, basestring):
            path = self.parse_path(path)
        self.join_to_path(path)
        field = self.get_field(path)
        sort_expr = field.prepare_order(self, path)
        if desc:
            sort_expr = sort_expr.desc()
        self.order_by_clauses.append(sort_expr)

    def finalize(self):

        if self.return_active is not None:
            self.where_clauses.append(self.base_table.c._active == self.return_active)

        query = sa.select(self.select_fields, use_labels=True).select_from(self.select_from)
        if self.where_clauses:
            query = query.where(sa.and_(*self.where_clauses))
        if self.order_by_clauses:
            query = query.order_by(*self.order_by_clauses)
        if self.group_by_clauses:
            query = query.group_by(*self.group_by_clauses)

        return query

    def extract(self, cur):
        """Extract entities from a SQLA row iterator.

        Uses :meth:`.Field.extract_select` for each field.

        :param res: The SQLA result iterator.
        :returns: iterator of entity dicts.

        """

        seen = set()
        id_col = self.base_table.c.id

        for raw_row in cur:

            # Filter out duplicates. This allows for a MUCH easier implementation
            # of multi_entity filters.
            id_ = raw_row[id_col]
            if id_ in seen:
                continue
            seen.add(id_)

            row = {'type': self.entity_type_name}
            for path, join_field, join_state, field, state in self.select_state:

                # Assert required joins actually happened.
                if join_field is not None:
                    if not join_field.check_for_join(self, raw_row, join_state):
                        continue

                try:
                    value = field.extract_select(self, raw_row, state)
                except NoFieldData:
                    pass
                else:
                    row[path.format()] = value
            yield row
