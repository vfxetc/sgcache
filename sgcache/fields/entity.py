import sqlalchemy as sa

from .core import sg_field_type, Field
from ..exceptions import FieldNotImplemented, FilterNotImplemented, NoFieldData, ClientFault



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
            return None
        return {'type': row[type_column], 'id': row[id_column]}

    def prepare_filter(self, req, path, relation, values):

        table = req.get_table(path)
        type_column = getattr(table.c, self.type_column.name)
        id_column = getattr(table.c, self.id_column.name)

        if relation in ('is', 'is_not', 'in', 'not_in'):

            # We could easily do this, but lets match Shotgun!
            if 'is' in relation and len(values) > 1:
                raise ClientFault('more than one value for %s' % relation)

            by_type = dict()
            for e in values:
                if e is None:
                    by_type[None] = [None]
                    continue
                try:
                    by_type.setdefault(e['type'], []).append(e['id'])
                except (TypeError, KeyError, IndexError):
                    raise ClientFault('multi_entity is value must be an entity')

            clauses = []
            for type_, ids in by_type.iteritems():
                if type_ is None:
                    clause = id_column == None
                else:
                    clause = sa.and_(
                        type_column == type_,
                        id_column.in_(ids)
                    )
                clauses.append(clause)

            clause = clauses[0] if len(clauses) == 1 else sa.or_(*clauses)
            if 'not' in relation:
                clause = sa.not_(clause)
                # We must specifically add a not-null.
                if None not in by_type:
                    clause = sa.or_(clause, id_column == None)

            return clause

        if relation in ('type_is', 'type_is_not'):
            if len(values) > 1:
                raise ClientFault('more than one value for %s' % relation)
            clause = type_column == values[0]
            if 'not' in relation:
                clause = sa.not_(clause)
                # We must specifically add a not-null.
                if values[0] is not None:
                    clause = sa.or_(clause, id_column == None)
            return clause

        raise FilterNotImplemented('%s on %s' % (relation, self.type_name))

    def prepare_upsert_data(self, req, value):
        if value is None:
            return {self.type_column.name: None,          self.id_column.name: None       }
        else:
            return {self.type_column.name: value['type'], self.id_column.name: value['id']}
