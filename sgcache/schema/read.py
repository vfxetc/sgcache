import sqlalchemy as sa


def parse_path(type_, path):
    path = path.split('.')
    res = [(type_, path.pop(0))]
    while path:
        res.append((path.pop(0), path.pop(0)))
    return res

def format_path(path):
    return '.'.join('%s.%s' % x for x in path)


class ReadRequest(object):

    def __init__(self, request):

        self.request = request
        self.entity_type_name = request['type']
        self.filters = request['filters']
        self.return_fields = request['return_fields']
        self.limit = request['paging']['entities_per_page']
        self.offset = self.limit * (request['paging']['current_page'] - 1)

        self.aliases = {}
        self.joined = set()
        self.select_fields = []
        self.select_from = None
        self.where_clauses = []

    def parse_path(self, path):
        return parse_path(self.entity_type_name, path)

    def get_entity(self, path):
        type_ = self.schema[path[-1][0]]
        return type_

    def get_field(self, path):
        type_ = self.schema[path[-1][0]]
        field = type_.fields[path[-1][1]]
        return field

    def get_table(self, path):
        parts = ['%s.%s' % x for x in path[:-1]]
        parts.append(path[-1][0])
        name = '.'.join(parts)
        if name not in self.aliases:
            self.aliases[name] = self.get_entity(path).table.alias(name)
        return self.aliases[name]

    def join(self, table, on):
        if table.name not in self.joined:
            self.select_from = self.select_from.outerjoin(table, on)
            self.joined.add(table.name)

    def prepare(self):

        self.select_from = self.get_table([(self.entity_type_name, None)])

        for raw_path in self.return_fields:
            path = self.parse_path(raw_path)
            #print 'prepare_join(s) for', format_path(path)
            for i in xrange(0, len(path) - 1):
                field_path = path[:i+1]
                field = self.get_field(field_path)
                field.prepare_join(self, field_path, path[:i+2])
            #print

            #print 'prepare_select for', format_path(path)
            field = self.get_field(path)
            field.prepare_select(self, path)
            #print

        for filter_ in self.filters['conditions']:
            path = self.parse_path(filter_['path'])
            relation = filter_['relation']
            values = filter_['values']

            #print 'prepare_filter for', format_path(path), relation, values

            field = self.get_field(path)
            clause = field.prepare_filter(self, path, relation, values)
            #print 'WHERE', clause
            if clause is not None:
                self.where_clauses.append(clause)

            #print

        query = sa.select(self.select_fields).select_from(self.select_from)

        if self.where_clauses:
            query = query.where(sa.and_(*self.where_clauses))

        return query

    def extract(self):
        pass

    def __call__(self, schema):

        self.schema = schema
        self.entity_type = schema[self.entity_type_name]

        query = self.prepare()

        #print query
        #print query.compile().params
        #print

        res = schema.db.execute(query)
        print 'RESULTS:'
        for i, row in enumerate(res):
            print i, row

        return self.extract()

        return self.entity_type

        '''

            "filters": {
                "conditions": [
                    {
                        "path": "field", 
                        "relation": "is", 
                        "values": [
                            // int:
                            123
                            // when datetime:
                            "2015-07-01T00:51:10Z"
                        ]
                    }
                ], 
                "logical_operator": "and"
            },

        '''
