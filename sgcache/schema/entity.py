import datetime

import sqlalchemy as sa
import migrate # this monkey-patches sqlalchemy

from .fields import sg_field_types


class EntityType(object):

    def __init__(self, schema, name, fields):

        self.schema = schema
        self.type_name = name
        self.table_name = name.lower()

        self.fields = {}
        for name, spec in fields.iteritems():
            
            # if it is a string, it represents just the data_type
            if isinstance(spec, basestring):
                spec = {'data_type': spec}
            else:
                spec = spec.copy()
            type_ = spec.pop('data_type')

            cls = sg_field_types[type_]
            field = self.fields[name] = cls(self, name, **spec)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.type_name)

    def __getitem__(self, key):
        return self.fields[key]
    def __contains__(self, key):
        return key in self.fields

    def _create_sql(self):
        
        self.table = self.schema.metadata.tables.get(self.table_name)
        if self.table is None:
            self.table = sa.Table(self.table_name, self.schema.metadata,
                sa.Column('id', sa.Integer, primary_key=True),
                sa.Column('_active', sa.Boolean, nullable=False, default=True),
            )
            self.table.create()
        
        if '_cache_created_at' not in self.table.c:
            # TODO: make these nullable
            sa.Column('_cache_created_at', sa.DateTime, default=datetime.datetime.utcnow).create(self.table)
            sa.Column('_cache_updated_at', sa.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow).create(self.table)
        if '_last_log_event_id' not in self.table.c:
            sa.Column('_last_log_event_id', sa.Integer).create(self.table)

        for field in self.fields.itervalues():
            field._create_sql(self.table)
