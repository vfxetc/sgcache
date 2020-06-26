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


When to Cache Data?
-------------------

We have a few opportunities to capture data as it is created/modified, and can
manufacture a few more:


.. _event_log:

1. The event log
^^^^^^^^^^^^^^^^

Anything a user does in the UI will be reflected in the
event log. Anything done by a  script with ``generate_events`` active
will also end up in the log.


2. Results of pass-through requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Anything returned from a request
we can't handle (e.g. an update, create, a read on a entity/field that is
uncached or a filter we don't support) can be inspected and cached.


.. _periodic_scans:

3. Periodic scans
^^^^^^^^^^^^^^^^^

Even if a script does not generate events, it will still affect the ``updated_at``
field on entities. Ergo, we can periodically scan every entity type, and request
all entities which have been changed since the last scan.


.. _execute_all_requests:

4. Executing all requests asynchronously
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Even if we are able to fully satisfy a read request, we can pass that request
through anyways and make sure that the data we returned matches.



Where to Cache Data?
--------------------

We use PostgreSQL (or SQLite in development) to store the data.

Shotgun also uses PostgreSQL, but is almost guaranteed to use it differently.

.. _db_schema_rules:


Schema Rules
^^^^^^^^^^^^

- Basic entities are stored in tables sharing the name of the entity type, e.g.:
  ``asset`` and ``shot``.

- Special fields (e.g. caching meta-data) are prefixed with an underscore.

- Columns generally take the field's name.

- All fields representing Shotgun data will be left nullable, unless we are
  absolutely certain they are not (e.g. :sg_field_type:`checkbox`).

- :sg_field_type:`multi_entity` fields will be represented as an association table named::
  
    {entity_type}_{field_name}

  We will not attempt to represent the ``*Connection`` entities, as we have so
  little of an understanding of how they work that we feel that we shouldn't even try.

  We will also not attempt to represent the bi-directional nature of Shotgun's
  multi-entity relationships (since we cannot trivially determine them with the
  public API), and instead rely upon the event log to update the inverse
  association.

- :sg_field_type:`entity` fields will be
  encoded with the entity type in ``{field_name}__type``
  and the id in ``{field_name}__id`` (note the double underscores).


Caveats
-------

The primary caveat that we must make is that in order for the cache to be
up to date (delayed only by the event loop) is that all script API keys
must generate events.

This is often disabled on some scripts in order to stop the massive amount of email
they can generate. However, there is no other way for the cache to be
immediately notified of changes.

In the future (i.e. when these features are implemented), you can reduce the
effect of non-event-generating scripts by decreasing the
delay between :ref:`update scans <periodic_scans>`, or you can
:ref:`execute all requests <execute_all_requests>` asynchronously.



