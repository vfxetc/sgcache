

class Passthrough(Exception):
    '''Signal that we cannot handle the request, but expect the real server can.'''


class EntityMissing(KeyError, Passthrough):
    '''Signal that a required entity does not exist in our schema.'''

class FieldMissing(KeyError, Passthrough):
    '''Signal that a required field does not exist in our schema.'''

class FieldNotImplemented(NotImplementedError, Passthrough):
    '''Signal that we don't implement anything about the given field.'''
    
class FilterNotImplemented(FieldNotImplemented, Passthrough):
    '''Signal that we can't process the requested filter.'''


class NoFieldData(KeyError):
    '''Non-error signal that requested data doesn't exist.'''


class Fault(ValueError):
    '''Mimicking a Shotgun fault.'''

    _default_code = 999

    @property
    def code(self):
        try:
            return self.args[1]
        except IndexError:
            return self._default_code


class ClientFault(Fault):

    _default_code = 103
