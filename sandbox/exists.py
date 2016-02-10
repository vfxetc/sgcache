
from sqlalchemy import *

engine = create_engine('sqlite://', echo=True)
meta = MetaData(bind=engine)
parent = Table('parent', meta,
    Column('id', Integer, primary_key=True),
    Column('value', Text, nullable=False),
)
child = Table('child', meta,
    Column('id', Integer, primary_key=True),
    Column('pid', Integer, ForeignKey('parent.id'), nullable=False),
    Column('value', Text, nullable=False),
)
meta.create_all()

print '=' * 78


q = select([parent.c.id]).where(
    exists().where(parent.c.id == child.c.pid)
)

engine.execute(parent.insert(), dict(id=1, value='child'))
engine.execute(parent.insert(), dict(id=2, value='no child'))
engine.execute(child.insert(), dict(id=1, pid=1, value='child 1 of 1'))
engine.execute(child.insert(), dict(id=2, pid=1, value='child 2 of 1'))
for row in engine.execute(q):
    print row
