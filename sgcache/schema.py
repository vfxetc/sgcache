import yaml


class Schema(dict):

    @classmethod
    def load_yaml(cls, fh):
        fh = open(fh) if isinstance(fh, basestring) else fh
        spec = yaml.load(fh.read())
        self = cls()
        for type_name, type_spec in spec.iteritems():
            self[type_name] = EntitySchema._from_yaml(type_name, type_spec)
        return self


class EntitySchema(dict):
    
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

    data_type = None
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


