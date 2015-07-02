System Design
=============

What Data to Cache?
-------------------

**All of it.**

Well, all of the data in the subset that we care about. It would be
awesome if the cache was only required to store the data that is actually
returned from the API, however it can't know that it is able to satisfy any
given query with the data is had unless it has everything.

So, we will pick a subset of entity types, and a subset of fields on those
types, and we will assume that we have every entity that will ever be requested
via the API.

A good boundary (for us) is to cut off old projects, however the cache will
have no knowledge of this.


Database
--------

We use PostgreSQL to store the data. Shotgun does the same, but is almost
guaranteed to use it differently.

Schema Rules
^^^^^^^^^^^^

- Basic entities are stored in tables sharing the name of the entity type, e.g.:
  ``Asset`` and ``Shot``.

- Special fields (e.g. flags for retirement) are prefixed with an underscore.

- Columns generally take the field's name.

- All fields representing Shotgun data will be left nullable, unless we are
  absolutely certain they are not (e.g. :sg_field_type:`checkbox`).

- :sg_field_type:`multi_entity` fields will be represented as an association table named::
  
    {entity_type}_{field_name}

  We will not attempt to represent the ``*Connection`` entities, as we have so
  little of an understanding of how they work that we feel that we shouldn't even try.

  We will also not attempt to represent the bi-directional nature of Shotgun's
  multi-entity relationships (since we cannot fully determine them with the
  public API), and instead rely upon the event log to update the inverse
  association.

- :sg_field_type:`entity` fields will be
  encoded with the entity type in ``{field_name}__type``
  and the id in ``{field_name}__id`` (note the double underscores).



