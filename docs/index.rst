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



Contents
--------

.. toctree::
   :maxdepth: 2

   setup
   design
   roadmap
   reverse_engineering
   dev_api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

