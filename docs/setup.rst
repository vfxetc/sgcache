Running the Cache
=================

Installation
------------

If you are going to cache a Shotgun installation of any significant size,
you should install the only non-Python dependency: `PostgreSQL <http://www.postgresql.org/>`_

You will also need `virtualenv <https://virtualenv.pypa.io/en/latest/>`_
for a non-system install (as is recommended).

A typical install looks like::

    # Grab the code
    git clone git@github.com:westernx/sgcache
    cd sgcache

    # Create a virtualenv, and install the Python dependencies
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-westernx.txt



Configuration
-------------

Configuration is provided by a cascade of information sourced from:

1. the default config in ``sgcache/config.py``;
2. environment variables prefixed with ``SGCACHE_``;
3. colon-delimited list of Python files specified by :attr:`~sgcache.config.CONFIG`

The recommended configuration setup is to write your own Python file with
your configuration changes, and refer to it via ``$SGCACHE_CONFIG``.



Execution
---------

The main entry point is the ``sgcache/__main__.py`` module, run via::

    python -m sgcache

All configuration options are exposed as command-line flags via :func:`.update_from_argv`::

    python -m sgcache --sqla-url postgres:///sgcache

Alternatively, place your configuration into another (Python) file, and reference it::

    python -m sgcache --config path/to/your/config.py



Configuration Reference
-----------------------

.. automodule:: sgcache.config
    :members:
