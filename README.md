# SGCache

## A Caching Shotgun Proxy

This project aims to be an intermediate service between the Shotgun API and its consumers, with the immediate major goals being to:

- Reduce the request latency compared to a hosted Shotgun server;

- Increase the redundancy of the Shotgun API, upon which we base (far too much) of our VFX pipeline;

- More flexibility in querying Shotgun data, as we may construct arbitrary queries against our own database if required.


Prospective longer term goals include:

- A simplistic web UI for use when Shotgun is unreachable;

- A host for more complex analyses of Shotgun data for introduction into Shotgun pages.


This project is in rapid active development, and is very near being deployable into production (with awareness of its caveats).


Please [read the docs](http://sgcache.readthedocs.org/en/latest/) for more, have fun, and good luck!

