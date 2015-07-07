import sqlalchemy as sa
import migrate # this monkey-patches sqlalchemy

from .fields import sg_field_types


class EntityType(object):

    def __init__(self, schema, name, fields):

        self.schema = schema
        self.type_name = name
        self.table_name = name.lower()

        self.fields = {}
        for name, (type_, kwargs) in fields.iteritems():
            cls = sg_field_types[type_]
            field = self.fields[name] = cls(self, name, **kwargs)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.type_name)

    def __getitem__(self, key):
        return self.fields[key]
    def __contains__(self, key):
        return key in self.fields

    def _create_sql(self):
        
        self.table = self.schema.metadata.tables.get(self.table_name)
        if not self.table:
            self.table = sa.Table(self.table_name, self.schema.metadata,
                sa.Column('id', sa.Integer, primary_key=True),
                sa.Column('_active', sa.Boolean, nullable=False, default=True),
            )
            self.table.create()

        for field in self.fields.itervalues():
            field._create_sql(self.table)
