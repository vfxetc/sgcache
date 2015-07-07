import re

import sqlalchemy as sa

from .entity import EntityType
from . import fields
from ..apimethods.read import ReadHandler
from ..apimethods.create import CreateHandler
from ..exceptions import EntityMissing



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
        try:
            return self._entity_types[key]
        except KeyError as e:
            raise EntityMissing(e.args[0])
    
    def __contains__(self, key):
        return key in self._entity_types
    
    def _create_sql(self):
        self.metadata.reflect()
        for entity in self._entity_types.itervalues():
            entity._create_sql()

    def read(self, request):
        handler = ReadHandler(request)
        return handler(self)

    def create(self, request, data=None, allow_id=False):

        if data is not None:
            request = {
                'type': request,
                'fields': [{'field_name': k, 'value': v} for k, v in data.iteritems()],
                'return_fields': ['id'],
            }
        
        handler = CreateHandler(request, allow_id=allow_id)
        return handler(self)

