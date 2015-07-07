

class Passthrough(ValueError):
    '''Signal that we cannot handle the request, but expect the real server can.'''


class EntityMissing(Passthrough):
    '''Signal that a required entity does not exist in our schema.'''

class FieldMissing(Passthrough):
    '''Signal that a required field does not exist in our schema.'''

class FilterNotImplemented(Passthrough):
    '''Signal that we can't process the requested filter.'''


class NoFieldData(KeyError):
    '''Non-error signal that requested data doesn't exist.'''

