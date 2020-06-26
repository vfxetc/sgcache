.. _index:

SGCache
=======

A Caching Shotgun Proxy
-----------------------

This project aims to be an intermediate service between the Shotgun API
and its consumers, with the immediate major goals being to:

.. _major_goals:

- Reduce the request latency compared to a hosted Shotgun server;

- Increase the redundancy of the Shotgun API, upon which we base (perhaps too much)
  of our VFX pipeline;

- More flexibility in querying Shotgun data, as we may construct arbitrary
  queries against our own database if required.

Prospective longer term goals include:

- A simplistic web UI for use when Shotgun is unreachable;

- A host for more complex analyses of Shotgun data for introduction into
  Shotgun pages.


Limitations
...........

At this point in the project, it should be a drop-in replacement for your use
of the Shotgun API, except in a few circumstances:

1. There is a slight delay for changes made in the Shotgun web UI to propagate
   to the cache as the cache must poll for changes. The default :data:`poll interval <sgcache.config.WATCH_IDLE_DELAY>`
   is 5 seconds.

2. API use which does not pass through the cache will not be immediately reflected
   in the cache if the API keys used do not generate events, and must wait for
   a scan for changes. The default :data:`scan interval <sgcache.config.SCAN_INTERVAL>` is 5 minutes.

3. The cache does not return the ``name`` :ref:`identifier_column` that Shotgun does.
   This is by design, but could be added as a configurable feature if there
   is enough demand.



Contents
--------

.. toctree::
   :maxdepth: 2

   setup
   design
   roadmap
   reverse_engineering
   dev-testing
   dev-api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
