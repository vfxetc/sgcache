Road Map
========

This project offers many opportunities to make a mistake that will be
incredibly difficult to isolate to the cache vs. the tools using it. Ergo,
we must be very careful in designing the stages of this project, and exactly
what they will and won't do, as backwards compatibility
is going to be a huge issue.

Herein lies our road map for the progression of this project.


1. Lazy, manual schema, and minimal UI
--------------------------------------

**This stage is complete!**

The first stage is to address all of our :ref:`major goals <major_goals>`
in a minimally viable, yet useful, form. That form includes:

- Representing a commonly used subset of the Shotgun schema;
- Having a copy of all of the data for a well-defined subset of entities
  (e.g. for recent projects)
- Fulfillment of basic read requests if we have enough information to respond confidently;
- Passing through all other requests to the real API, and caching their responses.
- Polling the real API's ``EventLogEntry`` entities to update our data in response
  to actions in the GUI.

To that end, we will make the following concessions:

- Pass through requests involving schema we do not store;
- Ignore any event pertaining to entities that we don't have
  access to, ignore, or whose mechanics are not 100% known;
- Ignore any event pertaining to schema changes;
- Ignore association of multi-entity columns; upon modifying;
  one, the event log will notify us of the change in associated column;
- Ignore specific columns (e.g. permanent fields matching ``*current_user*``) as their
  values are user-specific.


2. Automatic schema management
------------------------------

The second stage is to have the cache adapt to schema changes, and no longer
require a manually crafted schema. The extra steps to get there are:

- Watch the event log for schema changes;
- When there is a schema change, grab the entire public schema, diff it against
  what we have, drop any columns which have any modifications, and create new
  ones.

The concession is that since we are unable to be sure we will be forwards compatible
with how Shotgun may change the schema, we will simply destroy any data related
to a schema change, and need to re-cache it.


3. Cache Writes
---------------

If we are confident enough with our knowledge of the schema and a subset of
field types, we may write data to the cache before we even make the request
of the real API.

This will allow the cache to fully replace the API (for the subset we understand)
in the case that the real API is unreachable.
