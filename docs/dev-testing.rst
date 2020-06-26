Testing
=======

SGCache's automated tests have been pivotal for the rapid development of the project.

Given the nature of the application, testing is not trivial. You must run a series
of processes simultaneously.


1. PostgreSQL
-------------

You must have a Postgres database running. The `tests/env-sgmock.sh` file assumes
you are running Postgres locally, and have a `sgcache-mock` database. You can do this with::

    initdb var/postgres
    pg_ctl -D var/postgres start
    createdb sgcache-mock



2. SGMock
---------

The SGCache integration tests back onto SGMock_ as a mock Shotgun server.
By default, the integration tests will refuse to run against a production Shotgun
server, as they are rather chaotic.

Install SGMock, and run the server::

    sgmock-server

.. _SGMock: https://github.com/westernx/sgmock


3. SGCache
----------

The tests run against a running SGCache. The `tests/env-sgmock.sh` file can be
sourced into your environment to access the Postgres and SGMock as setup above::

    source tests/env-sgmock.sh
    sgcache-scanner --full # Prime the schema.
    sgcache-auto



4. Run the Tests!
-----------------

Use your favourite test runner::

    nosetests -x


