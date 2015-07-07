import re

import sqlalchemy as sa

from .entity import EntityType
from . import fields




class Schema(object):

    base_schema = dict(
        Step=dict(
            code=('text', {}),
            name=('text', {}),
        ),
        Project=dict(
            name=('text', {}),
        ),
        Asset=dict(
            name=('text', {}),
            project=('entity', {'entity_types': ['Project']}),
        ),
        Sequence=dict(
            name=('text', {}),
            project=('entity', {'entity_types': ['Project']}),
        ),
        Shot=dict(
            name=('text', {}),
            project=('entity', {'entity_types': ['Project']}),
            sg_sequence=('entity', {'entity_types': ['Sequence']}),
        ),
        Task=dict(
            content=('text', {}),
            project=('entity', {'entity_types': ['Project']}),
            entity=('entity', {'entity_types': ['Asset', 'Shot']}),
            step=('entity', {'entity_types': ['Step']}),
        ),
    )

    def __init__(self, db):
        
        self.db = db
        self.metadata = sa.MetaData()

        self._entity_types = {}
        for name, fields in self.base_schema.iteritems():
            fields['id'] = ('number', {})
            self._entity_types[name] = EntityType(self, name, fields)

        self._create_sql()

    def __getitem__(self, key):
        return self._entity_types[key]
    def __contains__(self, key):
        return key in self._entity_types
    
    def _create_sql(self):
        with self.db.begin() as con:
            for entity in self._entity_types.itervalues():
                entity._create_sql(con)

