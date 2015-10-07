import datetime

import sqlalchemy as sa


class Api3CreateOperation(object):

    """Operation to process an API3-style "create" request, which look like::

        {
            "fields": [
                {
                    "field_name": "key", 
                    "value": "value"
                }
            ], 
            "return_fields": [
                "id"
            ], 
            "type": "Test"
        }

    :param dict request: The request with ``fields``, ``return_fields``, and ``type``.
    :param bool create_with_id: If an ID is provided, and the entity does not
        exist, are we permitted to create that specific entity?
    :raises ValueError: if an ID is given but ``create_with_id`` is not true.

    """

    def __init__(self, request, create_with_id=False, source_event=None):

        self.entity_type_name = request['type']
        self.data = {x['field_name']: x['value'] for x in request['fields']}
        self.return_fields = request['return_fields']

        #: Did the entity exist? Set to ``True`` once run if an ID was provided
        #: and that entity did exist.
        self.entity_exists = None

        self.entity_id = self.data.get('id') # this is for field.prepare_upsert_data
        if self.entity_id and not create_with_id:
            raise ValueError('cannot specify ID for create')

        #: List of functions to call with the transaction before the primary query is
        #: executed; generally appended to by the ``multi_entity`` :class:`~sgcache.fields.Base`.
        self.before_query = []
        
        #: List of functions to call with the transaction after the primary query is
        #: executed; generally appended to by the ``multi_entity`` :class:`~sgcache.fields.Base`.
        self.after_query = []

        #: The :class:`~sgevents.event.Event` that triggered this query.
        self.source_event = source_event

    def run(self, cache, con=None, extra=None):
        """Run the create operation.

        :param cache: The :class:`Cache`.
        :param con: A SQLA connection; we will create one if not passed.
        :param dict extra: Extra data to insert/update in the entity; used
            for entity-level caching mechanisms.

        """

        query_params = (extra or {}).copy()

        # Manually deal with _active field, since it isn't actually a field
        # in the cache and so won't be handled by below.
        explicit_active = '_active' in self.data
        query_params['_active'] = self.data.get('_active', True)

        # Stuff in the current time for created/updated_at; the creation time
        # will be popped out if we determine that the entity already exists.
        query_params['_cache_created_at'] = query_params['_cache_updated_at'] = datetime.datetime.utcnow()

        for field_name, field in cache[self.entity_type_name].fields.iteritems():
            value = self.data.get(field_name)
            if value is not None:
                field_params = field.prepare_upsert_data(self, value)
                if field_params:
                    query_params.update(field_params)

        con = con or cache.db.connect()
        with con.begin():

            table = cache[self.entity_type_name].table

            # Determine if the entity exists (to determine if we need to
            # update or insert, but also for multi_entity fields to know
            # if they need to do pre-processing).
            if self.entity_id:
                self.entity_exists = list(con.execute(sa.select([table.c.id]).where(table.c.id == self.entity_id).limit(1)))

            # Callbacks for multi_entity fields.
            for func in self.before_query:
                func(con)

            if self.entity_exists:

                # Do not update these fields:
                del query_params['id']
                del query_params['_cache_created_at']

                # Allow _active during update if it was explicitly passed (e.g.
                # by something that is (un)retiring an entity at the same time
                # as creating/updating it).
                if not explicit_active:
                    del query_params['_active']

                # Update!
                con.execute(table.update().where(table.c.id == self.entity_id), **query_params)

            else:
                # Insert!
                res = con.execute(table.insert(), **query_params)
                self.entity_id = self.entity_id or res.inserted_primary_key[0]

            # Callbacks for multi_entity fields.
            for func in self.after_query:
                func(con)
        
        return {'type': self.entity_type_name, 'id': self.entity_id}


