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


Database
--------

SGCache generally operates with either of SQLite, or PostgreSQL (and maybe others,
as it uses SQLAlchemy as its database access layer).

SQLite is usually reserved for very small installations, or development. Production
environments should use PostgreSQL.


Schema
------

You must select the subset of the Shotgun schema that you want to cache,
and set :attr:`~sgcache.config.SCHEMA` to point to the containing YAML file.
The ``schema/keystone-basic.yml`` file demonstrates the format, and is
generated from our live Shotgun and basic rules via::

    ./schema/dump > schema/keystone-full.yml
    ./schema/filter --absent -f schema/basic-filters.txt schema/keystone-full.yml > schema/keystone-basic.yml

Changes
.......

To update the schema asserting the cache does not return invalid data, you must:

1. Update the schema YAML file.
2. Restart the event watcher and the periodic scanner.
3. Perform a complete scan.
4. Restart the web server only once the full scan finishes.

Restarting the web server prematurely will result in it assuming that the new
fields are empty, and return incomplete data.


Priming the Cache
-----------------

SGCache assumes that it knows about every entity in your Shotgun, so in order
to return correct results, you must perform a full scan::

    sgcache-scanner --scan-since 0

Once that scan is complete, you can leave the scanner running, or kill it with
``Ctrl-C``.


Running the Daemons
-------------------

The three primary daemons are ``sgcache-scanner``, ``sgcache-events``, and ``sgcache-web``.
It is recommended to run them seperately, but for convenience there is a ``sgcache-auto``
which will run them all.

All configuration options are exposed as command-line flags, but it is recommended
to create a ``config.py`` file, and refer to it via ``$SGCACHE_CONFIG``.


Reverse Proxying with Nginx
---------------------------

It is recommended to run SGCache behind an Nginx reverse proxy. This allows
Nginx to directly transfer of large files, as we have experienced trouble with
getting the cache to upload massive files itself.

Here is the Nginx config at Western Post::

    server {
        listen       80;
        server_name  sgcache.westernx;

        # Fails fast with file uploads without this.
        client_max_body_size 1G;

        # Pass large uploads/downloads to Shotgun.
        location ~ ^/(upload|thumbnail|file_serve) {
            proxy_set_header Host keystone.shotgunstudio.com;
            proxy_pass https://keystone.shotgunstudio.com;
        }

        # Everything else goes to SGCache.
        location / {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_pass http://127.0.0.1:8010;
        }

    }

Configuration Reference
-----------------------

.. automodule:: sgcache.config
