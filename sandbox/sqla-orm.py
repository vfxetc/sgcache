from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

engine = sa.create_engine('sqlite:///:memory:', echo=True)

Session = sessionmaker(bind=engine)

Base = declarative_base()
Base.metadata.bind = engine


class Project(Base):

    __tablename__ = 'project'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)


class Sequence(Base):

    __tablename__ = 'sequence'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)

    project__id = sa.Column(sa.Integer, sa.ForeignKey('project.id'))
    project = sa.orm.relationship('Project')


class Asset(Base):

    __tablename__ = 'asset'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)

    project__id = sa.Column(sa.Integer, sa.ForeignKey('project.id'))
    project = sa.orm.relationship('Project')


class Shot(Base):

    __tablename__ = 'shot'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)

    project__id = sa.Column(sa.Integer, sa.ForeignKey('project.id'))
    project = sa.orm.relationship('Project')

    sequence__id = sa.Column(sa.Integer, sa.ForeignKey('sequence.id'))
    sequence = sa.orm.relationship('Sequence')


Base.metadata.create_all()

s = Session()

p = Project(name='Master of Surrender')
sq = Sequence(project=p, name='AA')
sh = Shot(name='AA_001', sequence=sq)

s.add(sh)
s.commit()


s = Session()
x = s.query(Shot.name, Sequence.name).join(Sequence).first()
print x

