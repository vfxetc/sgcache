import functools
import re

import sqlalchemy as sa

from ..exceptions import FilterNotImplemented


sg_field_types = {}

def sg_field_type(cls):
    type_name = re.sub(r'(.)([A-Z][a-z])', r'\1_\2', cls.__name__).lower()
    cls.type_name = type_name
    sg_field_types[type_name] = cls
    return cls


class Base(object):

    def __init__(self, entity, name):
        self.entity = entity
        self.name = name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    def _create_or_check(self, table, column):
        existing = table.c.get(column.name)
        if existing is None:
            column.create(table)
            return column

        for attr in 'type', 'primary_key', 'foreign_keys', 'constraints':
            if attr == 'type':
                ev = existing.type.compile() 
                cv = column.type.compile()
            else:
                ev = getattr(existing, attr)
                cv = getattr(column, attr)

            if ev != cv:
                raise RuntimeError('schema mismatch on %s.%s; existing %s %r != %r' % (
                    table.name, column.name, attr, ev, cv
                ))
        return existing

    def _create_sql(self, table):
        raise NotImplementedError()

    def prepare_join(self, request, self_path, next_path):
        raise NotImplementedError()

    def prepare_select(self, req, path):
        column = getattr(req.get_table(path).c, self.name)
        req.select_fields.append(column)
        return column

    def prepare_order(self, req, path):
        column = getattr(req.get_table(path).c, self.name)
        return column

    def extract_select(self, req, path, row, column):
        return row[column]

    def prepare_filter(self, req, path, relation, values):
        column = getattr(req.get_table(path).c, self.name)
        if relation == 'is':
            return column == values[0]
        elif relation == 'is_not':
            return column != values[0]
        elif relation == 'in':
            return column.in_(values)
        elif relation == 'greater_than':
            return column > values[0]
        elif relation == 'less_than':
            return column < values[0]
        else:
            raise FilterNotImplemented('%s on %s' % (relation, self.type_name))

    def prepare_upsert(self, req, value):
        return {self.name: value}



class Scalar(Base):

    sa_type = None

    def _create_sql(self, table):
        self.column = self._create_or_check(table, sa.Column(self.name, self.sa_type))



@sg_field_type
class Checkbox(Scalar):
    sa_type = sa.Boolean



@sg_field_type
class Number(Base):

    def _create_sql(self, table):
        self.column = self._create_or_check(table, sa.Column(self.name, sa.Integer, primary_key=self.name == 'id'))


@sg_field_type
class Duration(Number):
    pass

@sg_field_type
class Percent(Number):
    pass

@sg_field_type
class Timecode(Number):
    pass



@sg_field_type
class Float(Scalar):
    sa_type = sa.Float



@sg_field_type
class Text(Scalar):
    sa_type = sa.Text
    
    def prepare_filter(self, req, path, relation, values):

        if relation == 'starts_with':
            column = getattr(req.get_table(path).c, self.name)
            return column.like(values[0].replace('%', '\\%') + '%')
        if relation == 'ends_with':
            column = getattr(req.get_table(path).c, self.name)
            return column.like('%' + values[0].replace('%', '\\%'))

        return super(Text, self).prepare_filter(req, path, relation, values)



@sg_field_type
class EntityType(Text):
    pass

@sg_field_type
class Color(Text):
    pass

@sg_field_type
class Image(Text):
    # TODO: affected by `api_return_image_urls`?
    pass

@sg_field_type
class List(Text):
    pass

@sg_field_type
class StatusList(Text):
    pass

@sg_field_type
class URLTemplate(Text):
    # TODO: affected by `api_return_image_urls`?
    pass

@sg_field_type
class UUID(Text):
    pass



@sg_field_type
class Date(Text):
    # TODO: understand this better
    pass

@sg_field_type
class DateTime(Text):
    # TODO: understand this better
    pass



@sg_field_type
class Entity(Base):

    def __init__(self, entity, name, entity_types):
        super(Entity, self).__init__(entity, name)
        self.entity_types = tuple(entity_types)

    def _create_sql(self, table):
        self.type_column = self._create_or_check(table, sa.Column('%s__type' % self.name, sa.Enum(*self.entity_types)))
        self.id_column   = self._create_or_check(table, sa.Column('%s__id' % self.name, sa.Integer))

    def prepare_join(self, req, self_path, next_path):
        self_table = req.get_table(self_path)
        next_table = req.get_table(next_path)
        req.join(next_table, sa.and_(
            self_table.c[self.type_column.name] == next_path[-1][0],
            self_table.c[self.id_column.name]   == next_table.c.id,
        ))

    def prepare_select(self, req, path):
        table = req.get_table(path)
        type_column = getattr(table.c, self.type_column.name)
        id_column = getattr(table.c, self.id_column.name)
        req.select_fields.extend((type_column, id_column))
        return type_column, id_column

    def extract_select(self, req, path, row, state):
        type_column, id_column = state
        if row[type_column] is None:
            raise KeyError(path)
        return {'type': row[type_column], 'id': row[id_column]}

    def prepare_filter(self, req, path, relation, values):

        table = req.get_table(path)
        type_column = getattr(table.c, self.type_column.name)
        id_column = getattr(table.c, self.id_column.name)

        if relation == 'is':
            return sa.and_(
                type_column == values[0]['type'],
                id_column == values[0]['id']
            )
        
        raise FilterNotImplemented('%s on %s' % (relation, self.type_name))

    def prepare_upsert(self, req, value):
        return {self.type_column.name: value['type'], self.id_column.name: value['id']}



@sg_field_type
class MultiEntity(Base):

    def __init__(self, entity, name, entity_types):
        super(MultiEntity, self).__init__(entity, name)
        self.entity_types = tuple(entity_types)

    def _create_sql(self, table):
        self.assoc_table_name = '%s_%s' % (table.name, self.name)
        self.assoc_table = table.metadata.tables.get(self.assoc_table_name)
        if self.assoc_table is None:
            # NOTE: we will need to handle any schema changes to this table ourselves
            self.assoc_table = sa.Table(self.assoc_table_name, table.metadata,
                sa.Column('id', sa.Integer, primary_key=True),
                sa.Column('parent_id', sa.Integer, sa.ForeignKey(table.name + '.id'), nullable=False),
                sa.Column('child_type', sa.Enum(*self.entity_types), nullable=False),
                sa.Column('child_id', sa.Integer, nullable=False)
            )
            self.assoc_table.create()

    def prepare_join(self, req, self_path, next_path):
        raise ValueError('you cant join through a multi-entity')

    def prepare_select(self, req, path):

        table = req.get_table(path)

        # get an alias of our table only if we need to
        alias_name = '%s_%s' % (table.name, self.name)
        assoc_table = self.assoc_table if self.assoc_table.name == alias_name else self.assoc_table.alias(alias_name) 

        req.join(assoc_table, assoc_table.c.parent_id == table.c.id)

        # we group by the parent_id such that only one row is actually
        # returned per parent entity
        req.group_by_clauses.append(assoc_table.c.parent_id)

        # we convert the group results into a comma-delimited string of results
        type_concat_field = sa.func.group_concat(assoc_table.c.child_type)
        id_concat_field = sa.func.group_concat(assoc_table.c.child_id)
        req.select_fields.extend((type_concat_field, id_concat_field))

        return (type_concat_field, id_concat_field)

    def extract_select(self, req, path, row, state):
        type_concat_field, id_concat_field = state
        if row[type_concat_field] is None:
            raise KeyError(path)
        return [{'type': type_, 'id': int(id_)} for type_, id_ in zip(row[type_concat_field].split(','), row[id_concat_field].split(','))]

    def prepare_filter(self, req, path, relation, values):
        raise FilterNotImplemented('%s on %s' % (relation, self.type_name))

    def prepare_upsert(self, req, value):
        if req.entity_id:
            # TODO: schedule deletion of existing data
            pass
        
        if req.entity_id:
            req.before_query.append(functools.partial(self._before_upsert, req, value))
        if value:
            req.after_query.append(functools.partial(self._after_upsert, req, value))

    def _before_upsert(self, req, value, con):
        # delete existing
        con.execute(self.assoc_table.delete().where(self.assoc_table.c.parent_id == req.entity_id))

    def _after_upsert(self, req, value, con):
        con.execute(self.assoc_table.insert(), [dict(
            parent_id=req.entity_id,
            child_type=entity['type'],
            child_id=entity['id']
        ) for entity in value])





@sg_field_type
class TagList(Base):
    # TODO: JSON?
    pass



@sg_field_type
class Serializable(Base):
    # TODO: JSON?
    pass



@sg_field_type
class URL(Base):
    # TODO: JSON?
    pass

