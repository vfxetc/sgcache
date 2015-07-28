import yaml


class Schema(dict):

    """A mapping of entity type names to :class:`EntitySchema`."""

    @classmethod
    def from_yaml(cls, fh):
        """from_yaml(cls, file)

        Load the full schema from the given YAML file. This schema is assumed to be:

        - a mapping of entity names to entity schemas, which are:
        - a mapping of field names to field schemas, which are:
        - either a string representing the data type, or a mapping including
          a ``data_type``, and any other info as required by the field.

        """
        fh = open(fh) if isinstance(fh, basestring) else fh
        spec = yaml.load(fh.read())
        self = cls()
        for type_name, type_spec in spec.iteritems():
            self[type_name] = EntitySchema._from_yaml(type_name, type_spec)
        return self


class EntitySchema(dict):
    
    """A mapping of field names to :class:`FieldSchema`."""

    def __init__(self, name):
        self.name = name

    @classmethod
    def _from_yaml(cls, name, spec):
        self = cls(name)
        self['id'] = FieldSchema._from_yaml('id', 'number')
        for field_name, field_spec in spec.iteritems():
            self[field_name] = FieldSchema._from_yaml(field_name, field_spec)
        return self

    def __repr__(self):
        return '<EntitySchema of %s: %r>' % (self.name, dict.__repr__(self))


class FieldSchema(object):

    """The schema of a single field."""

    #: The Shotgun data type, e.g. ``entity`` or ``checkbox``.
    data_type = None

    #: The allowable entity types for ``entity`` and ``multi_entity`` fields.
    entity_types = ()

    def __init__(self, name):
        self.name = name

    @classmethod
    def _from_yaml(cls, name, spec):
        self = cls(name)
        if isinstance(spec, basestring):
            spec = {'data_type': spec}
        self.__dict__.update(spec)
        if not self.data_type:
            raise ValueError('field needs data_type')
        return self


