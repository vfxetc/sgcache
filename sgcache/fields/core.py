from datetime import datetime, date
import re

import sqlalchemy as sa

from ..exceptions import FieldNotImplemented, FilterNotImplemented, NoFieldData, ClientFault


sg_field_types = {}

def sg_field_type(cls):
    type_name = re.sub(r'(.)([A-Z][a-z])', r'\1_\2', cls.__name__).lower()
    cls.type_name = type_name
    sg_field_types[type_name] = cls
    return cls


_schema_attribute_normalizations = {
    'type': {
        'DOUBLE PRECISION': 'FLOAT',
    }
}
def _normalize_schema_attribute(name, value):
    if not isinstance(value, basestring):
        return value
    return _schema_attribute_normalizations.get(name, {}).get(value, value)


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

            # For some reason, they still can come back a little wonky
            # on reflection.
            ev = _normalize_schema_attribute(attr, ev)
            cv = _normalize_schema_attribute(attr, cv)

            if ev != cv:
                raise RuntimeError('schema mismatch on %s.%s; existing %s %r != %r' % (
                    table.name, column.name, attr, ev, cv
                ))
        return existing

    def _construct_schema(self, table):
        raise NotImplementedError()

    def _clear(self, con):
        pass

    def is_cached(self):
        return True

    # Query construction methods
    # ==========================

    def prepare_deep_filter(self, read_op, self_path, next_path, final_path, relation, values):
        return None

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

    # Creating or updating an absent field is a failure.
    prepare_upsert_data = _raise


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
class DateTime(Text):
    def prepare_upsert_data(self, create_op, value):
        # We can get either strings or datetime[s]. If they are strings, we
        # assume they are properly formated; perhaps we should assert this
        # in the future. If they are datetime, we format them in the way that
        # the shotgun_api3 expects, otherwise they will be returned as strings.
        if isinstance(value, datetime):
            value = value.strftime('%Y-%m-%dT%H:%M:%SZ')
        return {self.name: value}

@sg_field_type
class Date(Text):
    def prepare_upsert_data(self, create_op, value):
        # See the comments on the DateTime field type.
        if isinstance(value, date):
            value = value.strftime('%Y-%m-%d')
        return {self.name: value}







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
