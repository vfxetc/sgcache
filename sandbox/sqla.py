import sqlalchemy as sa

engine = sa.create_engine('sqlite:///:memory:', echo=True)

metadata = sa.MetaData(bind=engine)


projects = sa.Table('project', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String),
)

col = sa.Column('project__id', sa.Integer, sa.ForeignKey('project.id'))
sequences = sa.Table('sequence', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String),
    col,
)

assets = sa.Table('asset', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String),
    sa.Column('project__id', sa.Integer, sa.ForeignKey('project.id')),
)

shots = sa.Table('shot', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String),
    sa.Column('project__id', sa.Integer, sa.ForeignKey('project.id')),
    sa.Column('sequence__id', sa.Integer, sa.ForeignKey('sequence.id')),
)

tasks = sa.Table('task', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String),
    sa.Column('entity__type', sa.String),
    sa.Column('entity__id', sa.Integer),
    sa.Column('project__id', sa.Integer, sa.ForeignKey('project.id')),
)

metadata.create_all()


project_id = projects.insert().execute(name='Master of Surrender').inserted_primary_key[0]
sequence_id = sequences.insert().execute(name='AA', project__id=project_id).inserted_primary_key[0]
shot_id = shots.insert().execute(name='AA_001', project__id=project_id, sequence__id=sequence_id).inserted_primary_key[0]
task_id = tasks.insert().execute(name='Animate', entity__type='Shot', entity__id=shot_id, project__id=project_id).inserted_primary_key[0]


sha = shots.alias()
sqa = sequences.alias()

q = sa.select([sha.c.id, sha.c.name, sqa.c.id, sqa.c.id, sqa.c.name]).select_from(
    sha.join(sqa, sha.c.sequence__id == sqa.c.id)
)

# print q


q = sa.select((tasks.c.id, tasks.c.name, shots.c.id, assets.c.id)).select_from(
    tasks
        .outerjoin(shots, sa.and_(tasks.c.entity__type == 'Shot', tasks.c.entity__id == shots.c.id))
        .outerjoin(assets, sa.and_(tasks.c.entity__type == 'Asset', tasks.c.entity__id == assets.c.id))
).where(sa.or_(shots.c.name.like("AA%"), assets.c.name.like("AA%")))

print q

print engine.execute(q).fetchall()
