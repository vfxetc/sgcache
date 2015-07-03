import urlparse
import contextlib
import logging

import psycopg2.pool
import psycopg2.extras
import psycopg2 as pg


log = logging.getLogger(__name__)


class Database(object):

    @classmethod
    def from_url(cls, url):
        parts = urlparse.urlsplit(url)
        return cls(host=parts.netloc, database=parts.path.strip('/').lower())

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._open_pool()

    def _open_pool(self):
        self._pool = pg.pool.ThreadedConnectionPool(0, 4, **self._kwargs)

    @contextlib.contextmanager
    def connect(self):
        con = self._pool.getconn()
        try:
            yield con
            con.commit()
        finally:
            self._pool.putconn(con)

    @contextlib.contextmanager
    def cursor(self):
        with self.connect() as con:
            with con.cursor() as cur:
                yield cur

    def reflect_columns(self, table_name):
        with self.cursor() as cur:
            cur.execute('''SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
            ''', [table_name.lower()]) # case insensitive!
            columns = set(row[0] for row in cur)
            # print columns
            return columns

    def update_schema(self):

        from .migrations import _migrations

        with self.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                ctime TIMESTAMP NOT NULL DEFAULT localtimestamp,
                name TEXT NOT NULL
            )''')
            cur.execute('SELECT name from schema_migrations')
            applied_patches = set(row[0] for row in cur)

        for name, func in _migrations:
            if name not in applied_patches:
                log.info('applying schema migration %s' % name)
                with self.cursor() as cur:
                    func(cur)
                    cur.execute('INSERT INTO schema_migrations (name) VALUES (%s)', [name])

    def destroy_schema(self):
        with self.cursor() as cur:
            cur.execute('''DROP TABLE IF EXISTS schema_migrations''')
