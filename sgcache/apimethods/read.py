import sqlalchemy as sa

from ..path import Path
from ..exceptions import EntityMissing, FieldMissing


class ReadHandler(object):

    def __init__(self, request):

        self.request = request
        self.entity_type_name = request['type']
        self.filters = request['filters']
        self.return_fields = request['return_fields']
        self.limit = request['paging']['entities_per_page']
        self.offset = self.limit * (request['paging']['current_page'] - 1)
        self.sorts = request.get('sorts', [])

        self.aliased = set()
        self.aliases = {}

        self.select_fields = []
        self.select_state = []

        self.select_from = None
        self.joined = set()

        self.where_clauses = []
        self.group_by_clauses = []
        self.order_by_clauses = []


    def parse_path(self, path):
        return Path(path, self.entity_type_name)

    def get_entity(self, path):
        try:
            type_ = self.schema[path[-1][0]]
        except KeyError as e:
            raise EntityMissing(e.args[0])
        return type_

    def get_field(self, path):
        type_ = self.get_entity(path)
        try:
            field = type_.fields[path[-1][1]]
        except KeyError as e:
            raise FieldMissing(e.args[0])
        return field

    def get_table(self, path):
        name = path.format(head=True, tail=False)
        if name not in self.aliases:
            # we can return the real table the first path it is used from,
            # but after that we must alias it
            table = self.get_entity(path).table
            if table.name in self.aliased:
                table = table.alias(name)
            self.aliased.add(table.name)
            self.aliases[name] = table
        return self.aliases[name]

    def join(self, table, on):
        if table.name not in self.joined:
            self.select_from = self.select_from.outerjoin(table, on)
            self.joined.add(table.name)

    def prepare_joins(self, path):
        for i in xrange(0, len(path) - 1):
            field_path = path[:i+1]
            field = self.get_field(field_path)
            field.prepare_join(self, field_path, path[:i+2])

    def prepare_filters(self, filters):

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

        self.select_from = self.get_table(Path([(self.entity_type_name, None)]))

        self.return_fields.append('id')
        
        for raw_path in self.return_fields:

            path = self.parse_path(raw_path)
            self.prepare_joins(path) # make sure it is availible

            field = self.get_field(path)
            state = field.prepare_select(self, path)

            self.select_state.append((path, field, state))

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
        rows = []
        for i, raw_row in enumerate(res):
            row = {'type': self.entity_type_name}
            for path, field, state in self.select_state:
                try:
                    value = field.extract_select(self, path, raw_row, state)
                except KeyError:
                    pass
                else:
                    row[path.format(head=False)] = value
            rows.append(row)
        return rows

    def __call__(self, schema):

        self.schema = schema
        self.entity_type = schema[self.entity_type_name]

        query = self.prepare()
        res = schema.db.execute(query)

        return self.extract(res)
