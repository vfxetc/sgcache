import collections
import datetime

import sqlalchemy as sa
import migrate # this monkey-patches sqlalchemy

from .fields import sg_field_types


class EntityType(collections.Mapping):

    """Largely a mapping of fields, but also responsible for entity-level
    caching mechanisms, including columns (on ``table.c``):

    - ``_active``: Is the entity not "retired"?
    - ``_cache_created_at``: When was this entity first cached?
    - ``_cache_updated_at``: When was this entity last updated in the cache?
    - ``_last_log_event_id``: What was the last ``LogEventEntry`` id to affect this entity?

    """

    def __init__(self, cache, name, schema):

        self.cache = cache

        #: The name of this entity type, e.g.: ``Task``.
        self.type_name = name

        #: The name of the SQLAlchemy table, usually the lower-cased ``type_name``;
        #: see :ref:`db_schema_rules`.
        self.table_name = name.lower()

        #: The SQLAlchemy table itself.
        self.table = None # just a stub for the docs, really.

        #: The :class:`EntitySchema` for this entity type.
        self.schema = schema

        self.fields = {}
        for name, field_schema in schema.iteritems():
            cls = sg_field_types[field_schema.data_type]
            field = self.fields[name] = cls(self, name, field_schema)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.type_name)

    def __getitem__(self, key):
        return self.fields[key]

    def __iter__(self):
        return iter(self.fields)

    def __len__(self):
        return len(self.fields)

    def _construct_schema(self):
        
        self.table = self.cache.metadata.tables.get(self.table_name)

        if self.table is None:
            self.table = sa.Table(self.table_name, self.cache.metadata,
                sa.Column('id', sa.Integer, primary_key=True),
                # We call this "active" to match the RPC values, even though
                # the Python API tends to call the negative of this "retired".
                sa.Column('_active', sa.Boolean, nullable=False, default=True),
            )
            self.table.create()
        
        if '_cache_created_at' not in self.table.c:
            # TODO: make these not-nullable
            sa.Column('_cache_created_at', sa.DateTime, default=datetime.datetime.utcnow).create(self.table)
            sa.Column('_cache_updated_at', sa.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow).create(self.table)
        if '_last_log_event_id' not in self.table.c:
            sa.Column('_last_log_event_id', sa.Integer).create(self.table)

        for field in self.fields.itervalues():
            field._construct_schema(self.table)
