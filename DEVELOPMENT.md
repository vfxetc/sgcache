SGCache Development
===================

Integration Testing
-------------------

SGCache's integration tests have been pivotal for the rapid development of the project.

Given the nature of the application, testing is not trivial. You must run a series
of processes simultaneously.


### 1. PostgreSQL

You must have a Postgres database running. The `tests/env-sgmock.sh` file assumes
you are running Postgres locally, and have a `sgcache-mock` database. You can do this with:

~~~
$ initdb var/pgdata
$ postgres -D var/pgdata
~~~

and from another terminal:

~~~
createdb sgcache-mock
~~~


### 2. SGMock

The SGCache integration tests back onto [SGMock][sgmock] as a mock Shotgun server.
By default, the integration tests will refuse to run against a production Shotgun
server, as they are rather chaotic.

Install SGMock, and run the server:

```
$ sgmock-server
2016-02-29 13:18:11,905     INFO sgmock: Running on http://127.0.0.1:8020/
```

[sgmock]: https://github.com/westernx/sgmock


### 3. SGCache

The tests run against a running SGCache. The `tests/env-sgmock.sh` file can be
sourced into your environment to access the Postgres and SGMock as setup above:

```
$ source tests/env-sgmock.sh
$ sgcache-scanner --full # Prime the schema.
$ sgcache-auto
```


### 4. Run the Tests!

Use your favourite test runner:

```
$ nosetests -x
........................
----------------------------------------------------------------------
Ran 24 tests in 6.705s

OK
```


