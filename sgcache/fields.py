import functools
import logging
import re

import sqlalchemy as sa

from .exceptions import FieldNotImplemented, FilterNotImplemented, NoFieldData, ClientFault
from .utils import iter_unique


log = logging.getLogger(__name__)


sg_field_types = {}

def sg_field_type(cls):
    type_name = re.sub(r'(.)([A-Z][a-z])', r'\1_\2', cls.__name__).lower()
    cls.type_name = type_name
    sg_field_types[type_name] = cls
    return cls


class Field(object):

    """The model of a single field of an entity, extended into a class
    for each and every of the different Shotgun data types.

    The functionality of the :class:`.Api3ReadOperation` and :class:`.Api3CreateOperation`
    depend upon the implementation of the following abstract methods:

    """

    def __init__(self, entity, name, schema):
        self.entity = entity
        self.name = name
        self.schema = schema

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    def _create_or_check(self, table, column):
        existing = table.c.get(column.name)
        if existing is None:
            column.create(table)
            return column

        for attr in 'type', 'primary_key', 'foreign_keys', 'constraints':
            if attr == 'type':
                # Compare the compiled version in the correct dialect to
                # correct for enums in different dialects.
                ev = existing.type.compile(table.metadata.bind.dialect) 
                cv = column.type.compile(table.metadata.bind.dialect)
            else:
                ev = getattr(existing, attr)
                cv = getattr(column, attr)

            if ev != cv:
                raise RuntimeError('schema mismatch on %s.%s; existing %s %r != %r' % (
                    table.name, column.name, attr, ev, cv
                ))
        return existing

    def _construct_schema(self, table):
        raise NotImplementedError()

    def is_cached(self):
        return True

    # Query construction methods
    # ==========================

    def prepare_join(self, read_op, self_path, next_path):
        """Prepare any joins required through this field.

        Only expected to be implemented by the ``Entity`` field class, this
        must call :meth:`.Api3ReadOperation.join` to include any required
        tables in the query.

        :param read_op: :class:`.Api3ReadOperation` that is running.
        :param self_path: :class:`.FieldPath` to this field in the context of the operation.
        :param next_path: :class:`.FieldPath` to the next field in the context of the operation.
        :return: An object to be passed back to :meth:`check_for_join` to
            establish if the join was successful or not.

        """

        raise NotImplementedError()

    def check_for_join(self, read_op, row, state):
        """Determine if the join set up by :meth:`prepare_join` occurred.

        :param read_op: :class:`.Api3ReadOperation` that is running.
        :param row: SQLAlchemy result row to inspect.
        :param state: Return value from previous :meth:`prepare_join`.
        :return bool: Did the requested join occur?

        """
        raise NotImplementedError()

    def prepare_select(self, read_op, path):
        """Select any fields that will be required to return the value of this field.

        This must extend :attr:`.Api3ReadOperation.select_fields` with any
        selectable expressions (e.g. columns) required by :meth:`extract_select`.

        :param read_op: :class:`.Api3ReadOperation` that is running.
        :param path: :class:`.FieldPath` to this field in the context of the operation.
        :return: An object to be passed back to :meth:`extract_select` to
            extract the value of this field for each returned row.

        """
        column = read_op.get_table(path).c[self.name]
        read_op.select_fields.append(column)
        return column

    def extract_select(self, read_op, row, state):
        """Extract the value for this field, raising :class:`NoFieldData`
        when no value should be returned.

        :param read_op: :class:`.Api3ReadOperation` that is running.
        :param row: The SQLAlchemy result row to extract values from.
        :param state: Return value from previous :meth:`prepare_select`.
        :return: Value to include in entity for this field.
        :raises NoFieldData: when no data should be returned.

        """
        try:
            return row[state] # state is the column
        except KeyError as e:
            raise NoFieldData()

    def prepare_order(self, read_op, path):
        """Prepare an expression to use for an order clause.

        :param read_op: :class:`.Api3ReadOperation` that is running.
        :param path: :class:`.FieldPath` to this field in the context of the operation.
        :return: A SQLA expression to use to order the rows.
        """
        return read_op.get_table(path).c[self.name]

    def prepare_filter(self, read_op, path, relation, values):
        """Prepare an expression to use for a where clause, and raise
        :class:`FilterNotImplemented` when the relation is not supported.

        :param read_op: :class:`.Api3ReadOperation` that is running.
        :param path: :class:`.FieldPath` to this field in the context of the operation.
        :param str relation: The request relation from the subset of those
            accepted by the Shotgun API, e.g. ``is``, ``in``, etc..
        :param tuple values: The values the operation uses.
        :return: A SQLA expression to use to filter the rows.
        :raises FilterNotImplemented: when the filter is not supported.

        """
        column = read_op.get_table(path).c[self.name]

        # Strings are case insensitive, so we use ILIKE.
        if relation in ('is', 'is_not') and isinstance(values[0], basestring):
            # This is quite awkward, but correct.
            pattern = re.sub(r'([\\%_])', '\\\\\\1', values[0])
            if relation == 'is':
                return column.ilike(pattern)
            else:
                return sa.not_(column.ilike(pattern))

        # TODO: How does case-insensitivity affect other comparisons?

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

    def prepare_upsert_data(self, create_op, value):
        """Prepare the data to insert or update for this field.

        If the data is more complex than can be dealt with in a single mapping
        (e.g. for ``multi_entity`` types), you can append callbacks to
        :attr:`~.Api3CreateOperation.before_query` and 
        :attr:`~.Api3CreateOperation.after_query` of the operation,
        which will be called with the database connection as the only argument.

        :param create_op: :class:`.Api3CreateOperation` that is running.
        :param value: The value to set.
        :return: ``dict`` of values to insert into the database.

        """
        return {self.name: value}



class Scalar(Field):

    sa_type = None

    def _construct_schema(self, table):
        self.column = self._create_or_check(table, sa.Column(self.name, self.sa_type))


@sg_field_type
class Absent(Field):
    """Special case, indicating that this field does not exist."""

    sa_type = None

    # Ignore a few methods; Shotgun silently discards fields that don't exist
    # in return_fields, and order.
    def _pass(self, *args, **kwargs):
        pass

    # Throw faults to match Shotgun's behaviour:
    # sgapi.core.ShotgunError: API read() Task.code doesn't exist:
    # {"values"=>["something"], "path"=>"code", "relation"=>"is"}
    def _raise(self, *args, **kwargs):
        raise ClientFault('%s.%s does not exist' % (self.entity.type_name, self.name))
    
    _construct_schema = _pass
    is_cached = _pass

    # Generally ignore the field, but do complain in a filter.
    prepare_filter = _raise
    prepare_join = _pass
    prepare_order = _pass
    prepare_select = _pass
    check_for_join = _pass

    # Need to signal that we have no data specifically.
    def extract_select(self, *args, **kwargs):
        raise NoFieldData()

    def prepare_upsert_data(self, req, value):
        # If triggered by an event, just ignore the request. This can happen
        # a lot with identifier columns (usually "name"), in which it seems
        # like we get a "name", but it really doesn't exist.
        if req.source_event:
            return
        else:
            self._raise()


class NonCacheableField(Field):
    """Special case, indicating that we don't support anything about this field."""

    sa_type = None

    def _pass(self, *args, **kwargs):
        pass

    def _raise(self, *args, **kwargs):
        raise FieldNotImplemented('%s.%s uses unsupported data_type "%s"' % (
            self.entity.type_name, self.name, self.schema.data_type
        ))

    _construct_schema = _pass
    is_cached = _pass

    prepare_filter = _raise
    prepare_join = _raise
    prepare_order = _raise
    prepare_select = _raise
    check_for_join = _raise
    extract_select = _raise # Should never be run.

    # Likely never to run. We would special case events like we do for
    # absent fields, except we don't expect to have anything that behaves
    # like "name" exist for a non-cacheable field.
    prepare_upsert_data = _raise 



@sg_field_type
class Checkbox(Scalar):
    sa_type = sa.Boolean



@sg_field_type
class Number(Field):

    # This might not be true...
    sa_type = sa.Integer

    def _construct_schema(self, table):
        self.column = self._create_or_check(table, sa.Column(self.name, self.sa_type, primary_key=self.name == 'id'))


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
class List(Text):
    pass

@sg_field_type
class StatusList(Text):
    # Despite the name, it is just a string.
    pass

@sg_field_type
class UUID(Text):
    # Just a string, but should reject non-UUID formatted ones.
    pass



@sg_field_type
class Date(Text):
    # TODO: understand this better
    # Just a string, but should reject malformed ones.
    pass

@sg_field_type
class DateTime(Text):
    # TODO: understand this better
    # Just a string, but should reject malformed ones.
    pass



@sg_field_type
class Entity(Field):

    def __init__(self, entity, name, schema):
        super(Entity, self).__init__(entity, name, schema)
        if not self.schema.entity_types:
            raise ValueError('entity field %s needs entity_types' % name)

    def _construct_schema(self, table):

        # We aren't confident using enumns yet since we don't know how to deal
        # with changes in them.
        if False:
            # We need to take care with enums, and create their type before the column.
            # If this is done on SQLite, it does nothing (as it should).
            type_enum = sa.Enum(*self.schema.entity_types, name='%s_%s__enum' % (table.name, self.name))
            type_column = sa.Column('%s__type' % self.name, type_enum)
            if type_column.name not in table.c:
                type_enum.create(table.metadata.bind)
        type_column = sa.Column('%s__type' % self.name, sa.String(255))

        # TODO: improve checking against existing types.
        self.type_column = self._create_or_check(table, type_column)
        self.id_column   = self._create_or_check(table, sa.Column('%s__id' % self.name, sa.Integer))

    def prepare_join(self, req, self_path, next_path):
        self_table = req.get_table(self_path)
        next_table = req.get_table(next_path)
        req.select_fields.append(next_table.c.id)
        req.join(next_table, sa.and_(
            self_table.c[self.type_column.name] == next_path[-1][0],
            self_table.c[self.id_column.name]   == next_table.c.id,
            next_table.c._active == True, # `retired_only` only affects the top-level entity
        ))
        return next_table.c.id

    def check_for_join(self, req, row, id_column):
        return bool(row[id_column])

    def prepare_select(self, req, path):
        table = req.get_table(path)
        type_column = getattr(table.c, self.type_column.name)
        id_column = getattr(table.c, self.id_column.name)
        req.select_fields.extend((type_column, id_column))
        return type_column, id_column

    def extract_select(self, req, row, state):
        type_column, id_column = state
        if row[type_column] is None:
            raise NoFieldData()
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

    def prepare_upsert_data(self, req, value):
        return {self.type_column.name: value['type'], self.id_column.name: value['id']}



@sg_field_type
class MultiEntity(Field):

    def __init__(self, entity, name, schema):
        super(MultiEntity, self).__init__(entity, name, schema)
        if not self.schema.entity_types:
            raise ValueError('entity field %s needs entity_types' % name)
    
    def _construct_schema(self, table):
        self.assoc_table_name = '%s_%s' % (table.name, self.name)
        self.assoc_table = table.metadata.tables.get(self.assoc_table_name)
        if self.assoc_table is None:
            # NOTE: we will need to handle any schema changes to this table ourselves
            self.assoc_table = sa.Table(self.assoc_table_name, table.metadata,
                sa.Column('id', sa.Integer, primary_key=True),
                sa.Column('parent_id', sa.Integer, sa.ForeignKey(table.name + '.id'), index=True, nullable=False),
                sa.Column('child_type', sa.String(255), nullable=False), #sa.Enum(*self.entity_types, name=table.name + '__enum'), nullable=False),
                sa.Column('child_id', sa.Integer, nullable=False)
            )
            self.assoc_table.create()

    def prepare_join(self, req, self_path, next_path):
        raise ValueError('you cant join through a multi-entity')

    def prepare_select(self, req, path):

        table = req.get_table(path)

        # Get an alias of our table (but only if we need to).
        alias_name = '%s_%s' % (table.name, self.name)
        assoc_table = self.assoc_table if self.assoc_table.name == alias_name else self.assoc_table.alias(alias_name) 

        # Postgres will aggregate into an array for us, but for SQLite
        # we convert the group results into a comma-delimited string of results
        # that must be split up later.
        group_func = getattr(sa.func, 'array_agg' if table.metadata.bind.dialect.name == 'postgresql' else 'group_concat')
        type_concat_field = group_func(assoc_table.c.child_type).label('child_types')
        id_concat_field = group_func(assoc_table.c.child_id).label('child_ids')

        # In order to use the aggregating functions, we must GROUP BY.
        # But, we need to avoid GROUP BY in the main query, as Postgres will
        # yell at us if we don't use aggregating functions for every other
        # column. So, we express ourselves in a subquery.
        subquery = (sa
            .select([
                assoc_table.c.parent_id.label('parent_id'),
                type_concat_field,
                id_concat_field
            ])
            .select_from(assoc_table)
            .group_by(assoc_table.c.parent_id)
        ).alias(alias_name + '__grouped')

        # TODO: somehow filter retired entities

        # Hopefully the query planner is smart enough to restrict the subquery...
        req.join(subquery, subquery.c.parent_id == table.c.id)

        fields_to_select = (subquery.c.child_types, subquery.c.child_ids)
        req.select_fields.extend(fields_to_select)

        return fields_to_select

    def extract_select(self, req, row, state):

        type_concat_field, id_concat_field = state
        if not row[type_concat_field]:
            return []

        # Postgres will return an array, while SQLite will return a string.
        types = row[type_concat_field]
        ids = row[id_concat_field]
        if isinstance(types, basestring):
            types = types.split(',')
            ids = ids.split(',')

        # Return unique entities since I don't think you can have the same
        # entity in a multi-entity twice.
        return [{'type': type_, 'id': int(id_)} for type_, id_ in iter_unique(zip(types, ids))]

    def prepare_filter(self, req, path, relation, values):
        raise FilterNotImplemented('%s on %s' % (relation, self.type_name))

    def prepare_upsert_data(self, req, value):
        if req.entity_id:
            # Schedule deletion of existing data.
            req.before_query.append(functools.partial(self._before_upsert, req, value))

        if value:
            # Schedule creation of new data.
            req.after_query.append(functools.partial(self._after_upsert, req, value))

    def _before_upsert(self, req, value, con):

        # We have a special syntax for handling changes from the event log
        if isinstance(value, dict) and '__removed__' in value:
            removed = value['__removed__']
            if not removed:
                return
            con.execute(self.assoc_table.delete().where(sa.and_(self.assoc_table.c.parent_id == req.entity_id, sa.or_(*[sa.and_(
                self.assoc_table.c.child_type == e['type'],
                self.assoc_table.c.child_id == e['id']
            ) for e in removed]))))

        # Delete existing
        else:
            con.execute(self.assoc_table.delete().where(self.assoc_table.c.parent_id == req.entity_id))

    def _after_upsert(self, req, value, con):

        # We have a special syntax for handling changes from the event log
        if isinstance(value, dict) and '__added__' in value:
            value = value['__added__']

        if not value:
            return

        con.execute(self.assoc_table.insert(), [dict(
            parent_id=req.entity_id,
            child_type=entity['type'],
            child_id=entity['id']
        ) for entity in value])





@sg_field_type
class Image(NonCacheableField):
    # May need to locally cache contents.
    pass

@sg_field_type
class PivotTable(NonCacheableField):
    # This one does respond to the API at all AFAICT.
    pass

@sg_field_type
class URLTemplate(NonCacheableField):
    # Needs template rendering.
    # Can't be used in a filter.
    pass

@sg_field_type
class TagList(NonCacheableField):
    # List of strings, AFAICT.
    # Can be used in a filter to some degree.
    pass

@sg_field_type
class Serializable(NonCacheableField):
    # Does not respond to much of the API, and only in EventLogEntry.
    # Can't be used in a filter.
    pass

@sg_field_type
class URL(NonCacheableField):
    # May need to locally cache contents.
    # Can't be used in a filter.
    pass

