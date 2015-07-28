
Development API
===============

This page is generally for the developers of sgcache itself, as it does
not yet have any Python API's designed for public consumption.


Cache Models
------------

.. automodule:: sgcache.cache

.. autoclass:: sgcache.cache.Cache

    .. automethod:: create_or_update

    .. automethod:: watch

    .. automethod:: scan

    .. automethod:: get_last_event


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


Schema
------

.. automodule:: sgcache.schema
    :members:


Field Paths
-----------

.. automodule:: sgcache.path

.. autoclass:: sgcache.path.FieldPath
    :members:

.. autoclass:: sgcache.path.FieldPathSegment
    :members:


API3 Operations
---------------

.. automodule:: sgcache.api3.create
    :members:

.. automodule:: sgcache.api3.read
    :members:
