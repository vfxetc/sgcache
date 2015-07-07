import sqlalchemy as sa


sg_field_types = {}

def sg_field_type(cls):
    type_name = getattr(cls, 'type_name', None) or cls.__name__.lower()
    cls.type_name = type_name
    sg_field_types[type_name] = cls
    return cls


class Base(object):

    def __init__(self, entity, name):
        self.entity = entity
        self.name = name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    def _init_columns(self):
        raise NotImplementedError()

    def _create_sql(self, con, columns):
        raise NotImplementedError()

    def prepare_join(self, request, self_path, next_path):
        raise NotImplementedError()

    def prepare_select(self, req, path):
        column = getattr(req.get_table(path).c, self.name)
        req.select_fields.append(column)
        return column

    def prepare_filter(self, req, path, relation, values):
        column = getattr(req.get_table(path).c, self.name)
        if relation == 'is':
            return column == values[0]
        else:
            raise NotImplementedError('%s on %s' % (relation, self.type_name))


@sg_field_type
class Number(Base):

    def _init_columns(self):
        self.column = sa.Column(self.name, sa.Integer, primary_key=self.name == 'id')
        return [self.column]

    def _create_sql(self, con, columns):
        if self.name in columns:
            return
        con.execute('''ALTER TABLE %s ADD COLUMN %s INTEGER''' % (self.entity.type_name, self.name))


@sg_field_type
class Text(Base):

    def _init_columns(self):
        self.column = sa.Column(self.name, sa.Text)
        return [self.column]

    def _create_sql(self, con, columns):
        if self.name in columns:
            return
        con.execute('''ALTER TABLE %s ADD COLUMN %s TEXT''' % (self.entity.type_name, self.name))


@sg_field_type
class EntityField(Base):

    type_name = 'entity'

    def __init__(self, entity, name, entity_types):
        super(EntityField, self).__init__(entity, name)
        self.entity_types = tuple(entity_types)

    def _init_columns(self):
        self.type_column = sa.Column('%s__type' % self.name, sa.String)
        self.id_column = sa.Column('%s__id' % self.name, sa.Integer)
        return [self.type_column, self.id_column]

    def _create_sql(self, con, columns):
        if '%s__id' % self.name in columns:
            return
        con.execute('''ALTER TABLE %s ADD COLUMN %s__type TEXT''' % (self.entity.type_name, self.name))
        con.execute('''ALTER TABLE %s ADD COLUMN %s__id INTEGER''' % (self.entity.type_name, self.name))

    def prepare_join(self, req, self_path, next_path):
        self_table = req.get_table(self_path)
        next_table = req.get_table(next_path)
        req.join(next_table, sa.and_(
            getattr(self_table.c, self.type_column.name) == next_path[-1][0],
            getattr(self_table.c, self.id_column.name) == next_table.c.id,
        ))

    def prepare_select(self, req, path):
        table = req.get_table(path)
        type_column = getattr(table.c, self.type_column.name)
        id_column = getattr(table.c, self.id_column.name)
        req.select_fields.extend((type_column, id_column))
        return type_column, id_column



