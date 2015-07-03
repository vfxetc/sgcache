

from .entity import Entity
from . import fields


class Project(Entity):

    name = fields.Text



class Schema(object):

    entity_classes = [Project]

    def __init__(self, db):
        self.db = db
        self._entities = {cls.type: cls(self, db) for cls in self.entity_classes}

    def __getitem__(self, key):
        return self._entities[key]
    def __contains__(self, key):
        return key in self._entities
    
    def assert_exists(self):
        for entity in self._entities.itervalues():
            entity.assert_exists()
