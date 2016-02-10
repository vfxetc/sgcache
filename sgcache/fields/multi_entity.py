import functools

import sqlalchemy as sa

from .core import sg_field_type, Field
from ..exceptions import FieldNotImplemented, FilterNotImplemented, NoFieldData, ClientFault
from ..utils import iter_unique


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

    def _clear(self, con):
        con.execute(self.assoc_table.delete())

    def prepare_join(self, req, self_path, next_path, for_filter):

        # We can only join through multi_entity for a filter.
        if not for_filter:
            return

        raise FieldNotImplemented() # until we figure this out

        self_table = req.get_table(self_path)
        next_table = req.get_table(next_path)
        join_table = self.assoc_table.alias() # Must always be unique.

        req.join(join_table, self_table.c.id == join_table.c.parent_id)
        req.join(next_table, sa.and_(
            join_table.c.child_type == next_path[-1][0],
            join_table.c.child_id   == next_table.c.id,
            next_table.c._active == True, # `retired_only` only affects the top-level entity
        ))

        req.select_fields.append(join_table.c.parent_id)

        # XXX: This no longer exists.
        req.row_post_filters.append(lambda row: row[join_table.c.parent_id] is not None)



    def check_for_join(self, req, row, state):
        # We don't return anything linked deeply through a multi_entity.
        pass

    def prepare_select(self, req, path):

        table = req.get_table(path)

        assoc_table = req.get_table(path, self.assoc_table, include_tail=True)

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
        ).alias(assoc_table.name + '__grouped')

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
