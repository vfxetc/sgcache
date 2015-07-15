Reverse Engineering
===================

Herein lies the more complex matters that we have discovered about Shotgun
while poking through it in order to create SGCache.

.. note:: This information is as of ``v6.0.3 (build 04eae45)``.


Field Types
-----------

.. warning:: Much of this information is incomplete. Especially null-ability;
             assume fields are null-able unless they say otherwise.

.. sg_field_type:: checkbox

    - API type: ``bool``
    - Not NULL-able; the API throws an error if you filter with a ``None`` here

.. sg_field_type:: color

    - API type: comma-delimited RGB integers, e.g.::

        "255,255,255"

      or one of::

        {"Blue", "Orange", "Pink", "Red", "Green", "Purple", "Grey", "Black"}

      or::

        "pipeline_step" # to use the colour from the Task's pipeline Step.

    - NULL-able in general, but not on :sg_field:`Task.color`; throw the error:

        Unsupported format for Task color field. The Task color can not be nil, the expected format is r,g,b where the values of r,g and b are in the range 0-255. The value of the color can also be set using the legacy color strings which are; Blue, Orange, Pink, Red, Green, Purple, Grey and Black. The value can also be set to the value pipeline_step to indicate that the Gantt bar should render using the color of the Task's Pipeline Step.



.. sg_field_type:: date

    - Python API type: :class:`datetime.date` object
    - JSON API type: (assumed) `ISO 8601 <https://en.wikipedia.org/?title=ISO_8601>`_ encoded string, e.g.::

        "2014-08-08"

.. sg_field_type:: date_time

    - Python API type: :class:`datetime.datetime` object
    - JSON API type: `ISO 8601 <https://en.wikipedia.org/?title=ISO_8601>`_ encoded string, e.g.::

        "2014-08-08T19:53:50Z"

.. sg_field_type:: duration

    - API type: ``int``

.. sg_field_type:: entity

    - API type: ``dict`` of a single entity; e.g.::

        {
            "id": 2,
            "type": "Shot",
            "name": "Shot 1"
        }

    - Must contain ``type`` and ``id``, and often ``name``
    - NULL-able
    - Not necessarily constrained to a single entity type

.. sg_field_type:: entity_type

    - API type: ``str`` of type name

.. sg_field_type:: float

    - API type: ``float``

.. sg_field_type:: image

    - API type: ``str`` of URL
    - May be influenced by ``api_return_image_urls`` passed via JSON API

.. sg_field_type:: list

    - API type: ``str``, value of which is from a defined set
    - A better name would be "enumeration"

.. sg_field_type:: multi_entity

    - API type: a ``list`` of :sg_field_type:`entities <entity>`

.. sg_field_type:: number

    - API type: ``int``
    - This is used for IDs

.. sg_field_type:: password

    - API type: the literal string ``'*******'``
    - Only used for ``ClientUser.password_proxy``

.. sg_field_type:: percent

    - API type: ``int`` from 0 to 100
    - Only used by ``Task.time_percent_of_est``

.. sg_field_type:: pivot_column

    - Only in ``step_*`` fields
    - Not supported by the API in any way

.. sg_field_type:: serializable

    - API type: any JSON
    - Not filterable by the API

.. sg_field_type:: status_list

    - API type: ``str``, value of which is from the set of statuses.

.. sg_field_type:: tag_list

    - API type: ``list`` of ???.

.. sg_field_type:: text

    - API type: ``str``
    - NULL-able.

.. sg_field_type:: timecode

    - API type: ``int``
    - Only used by ``Shot.{src_in,src_out}``

.. sg_field_type:: url

    - API type: ``dict`` with:
        - ``content_type``
        - ``name``
        - etc.,
    - Appears to be a link to the entity it belongs to, and so violates a core
      assumption that SGSession makes.
    - Cannot be used in filters

.. sg_field_type:: url_template

    - Not filterable by the API
    - Not used by default; only by by our ``{Shot,Version}.sg_viewer_link``
      (which itself is deprecated)

.. sg_field_type:: uuid

    - API Type: ``str`` of typical `UUID <https://en.wikipedia.org/wiki/Universally_unique_identifier>`_,
      e.g.::

        "de305d54-75b4-431b-adb2-eb6b9e546014"



Event Logs
----------

.. seealso:: `sgevent's documentation on the event log <http://sgevents.readthedocs.org/en/latest/reverse_engineering.html>`_
