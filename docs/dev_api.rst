
Development API
===============

This page is generally for the developers of sgcache.


Schema
------

.. automodule:: sgcache.cache

.. autoclass:: sgcache.cache.Cache

    .. automethod:: create_or_update

    .. automethod:: get_last_event()

    .. automethod:: watch

    .. automethod:: scan


Entities
~~~~~~~~

.. automodule:: sgcache.entity
    :members:


Fields
~~~~~~

.. automodule:: sgcache.fields

.. autoclass:: sgcache.fields.Base
    :members:

.. autoclass:: sgcache.fields.Entity

.. autoclass:: sgcache.fields.MultiEntity


Field Paths
-----------

.. automodule:: sgcache.path

.. autoclass:: sgcache.path.FieldPath
    :members:

.. autoclass:: sgcache.path.FieldPathSegment
    :members:


