from psycopg2 import ProgrammingError as DBError


class Base(object):

    def __init__(self, entity, name, db):
        self._entity = entity
        self.name = name
        self.db = db

    def assert_exists(self):
        raise NotImplementedError()


class Text(Base):

    def assert_exists(self):
        if self.name in self.db.reflect_columns(self._entity.type):
            return
        with self.db.cursor() as cur:
            cur.execute('''ALTER TABLE %s ADD COLUMN %s text''' % (self._entity.type, self.name))


