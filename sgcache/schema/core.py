import re

import sqlalchemy as sa

from .entity import EntityType
from . import fields




class Schema(object):

    def __init__(self, db, spec):
        
        self.db = db
        self.spec = spec
        self.metadata = sa.MetaData(bind=db)

        self._entity_types = {}
        for name, fields in self.spec.iteritems():
            fields['id'] = 'number'
            self._entity_types[name] = EntityType(self, name, fields)

        self._create_sql()

    def __getitem__(self, key):
        return self._entity_types[key]
    def __contains__(self, key):
        return key in self._entity_types
    
    def _create_sql(self):
        self.metadata.reflect()
        for entity in self._entity_types.itervalues():
            entity._create_sql()

