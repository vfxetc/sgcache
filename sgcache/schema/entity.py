
from .fields import Base as _BaseField


class _EntityMeta(type):

    def __new__(mcls, name, bases, namespace):

        # assign an entity type if it doesn't explicitly have one
        namespace.setdefault('type', name)

        field_classes = namespace.setdefault('field_classes', {})
        for base in bases:
            field_classes.update(getattr(base, 'field_classes', {}))
        for name, value in namespace.iteritems():
            try:
                if issubclass(value, _BaseField):
                    field_classes[name] = value
            except TypeError:
                pass

        return super(_EntityMeta, mcls).__new__(mcls, name, bases, namespace)


class Entity(object):

    __metaclass__ = _EntityMeta

    def __init__(self, schema, db):
        self._schema = schema
        self.db = db
        self._fields = {name: cls(self, name, db) for name, cls in self.field_classes.iteritems()}

    def __getitem__(self, key):
        return self._fields[key]
    def __contains__(self, key):
        return key in self._fields

    def assert_exists(self):
        
        with self.db.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS %s (
                id SERIAL,
                _active BOOLEAN DEFAULT true
            )''' % (self.type, ))

        for field in self._fields.itervalues():
            field.assert_exists()
