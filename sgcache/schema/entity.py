import sqlalchemy as sa

from .fields import sg_field_types


class EntityType(object):

    def __init__(self, schema, name, fields):

        self.schema = schema
        self.type_name = name.title()
        self.table_name = name.lower()

        self.fields = {}
        field_columns = []
        for name, (type_, kwargs) in fields.iteritems():
            cls = sg_field_types[type_]
            field = self.fields[name] = cls(self, name, **kwargs)
            field_columns.extend(field._init_columns())

        self.table = sa.Table(self.table_name, schema.metadata,
            # sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('_active', sa.Boolean, nullable=False),
            *field_columns
        )

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.type_name)

    def __getitem__(self, key):
        return self.fields[key]
    def __contains__(self, key):
        return key in self.fields

    def _create_sql(self, con):
        
        inspector = sa.inspect(con)
        raw_columns = inspector.get_columns(self.table_name)
        columns = {c['name']: c for c in raw_columns}

        if not columns:
            con.execute('''CREATE TABLE %s (
                id INTEGER PRIMARY KEY, -- what must this be for Postgres?
                _active BOOLEAN DEFAULT true
            )''' % (self.table_name))

        for field in self.fields.itervalues():
            if field.name == 'id':
                continue
            field._create_sql(con, columns)
