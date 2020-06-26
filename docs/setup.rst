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
    git clone git@github.com:vfxetc/sgcache
    cd sgcache

    # Create a virtualenv, and install the Python dependencies
    virtualenv venv
    . activate.sh
    pip install -r requirements.txt

Configuration
-------------

Configuration is provided by a cascade of information sourced from:

1. the default config in ``sgcache/config.py``;
2. environment variables prefixed with ``SGCACHE_``;
3. colon-delimited list of Python files specified by :attr:`~sgcache.config.CONFIG`

The recommended configuration setup is to write your own Python file with
your configuration changes, and refer to it via ``$SGCACHE_CONFIG``. The default
``activate.sh`` will pull in a file at ``var/config.py``.


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

    mkdir -p var/schema
    ./schema/dump > var/schema/full.yml
    ./schema/filter --file schema/basic-filters.txt var/schema/full.yml > var/schema/basic.yml

Changes
.......

To update the schema asserting the cache does not return invalid data, you must:

1. Update the schema YAML file.
2. Restart the event watcher and the periodic scanner.
3. Perform a complete scan of the modified types::

    sgcache-scanner --full --scan-types Shot,Task

4. Restart the web server only once the full scan finishes.

Restarting the web server prematurely will result in it assuming that the new
fields are empty, and return incomplete data.


Priming the Cache
-----------------

SGCache assumes that it knows about every entity in your Shotgun, so in order
to return correct results, you must perform a full scan::

    sgcache-scanner --full

If you are testing, you can specify individual projects to cache::

    sgcache-scanner --full --scan-projects 66,67


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

Here is an example Nginx config::

    server {
        listen       80;
        server_name  sgcache.EXAMPLE.com;

        # Fails fast with file uploads without this.
        client_max_body_size 1G;

        # Pass large uploads/downloads to Shotgun.
        location ~ ^/(upload|thumbnail|file_serve) {
            proxy_set_header Host EXAMPLE.shotgunstudio.com;
            proxy_pass https://EXAMPLE.shotgunstudio.com;
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
