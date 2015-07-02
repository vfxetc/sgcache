import logging


logging.getLogger(None).setLevel(100)


from py2neo import Graph, Node, Relationship
from shotgun_api3_registry import connect
from sgsession import Session, Entity

db = Graph('http://neo4j:password@sg55.keystone:7474/db/data')
sg = Session(connect())


if False:
    for row in db.cypher.execute('''
        MATCH (p:Project {name: {name}})<-[e]-(ref)
        RETURN p, e, ref
    ''', {'name': "Testing Sandbox"}):
        print row.p.properties['name'], row.e.type, row.ref.properties['code']
    exit()


def create_or_update_node(entity):

    node = db.merge_one(entity['type'], 'id', entity['id'])
    tx = db.cypher.begin()

    for key, value in entity.iteritems():
        if isinstance(value, Entity):
            _create_or_update_link(tx, entity, key, value)
        elif isinstance(value, (list, tuple)):
            _create_or_update_link(tx, entity, key, delete=True)
            for v2 in value:
                assert isinstance(v2, Entity)
                _create_or_update_link(tx, entity, key, v2, delete=False)
        else:
            node.properties[key] = value

    # TODO: get these into the same transaction
    node.push()
    tx.commit()


def _create_or_update_link(tx, entity, key, value=None, delete=True):

    # delete existing relationships
    if delete:
        tx.append('''
            MATCH (e:%s {id:{id}}) -[r:%s]-> ()
            DELETE r
        ''' % (entity['type'], key), id=entity['id'])

    if value is not None:
        # assert the target node exists
        tx.append('''
            MERGE (e:%s {id:{id}})
        ''' % value['type'], value)

        # create the relationship
        tx.append('''
            MATCH (a:%s {id:{lid}}), (b:%s {id: {rid}})
            MERGE (a)-[r:%s]->(b)
            RETURN r
        ''' % (entity['type'], value['type'], key), lid=entity['id'], rid=value['id'],
        )


if False:
    for proj in sg.find('Project', []):
        create_or_update_node(proj)
        for seq in sg.find('Sequence', [('project', 'is', proj)]):
            create_or_update_node(seq)

if False:
    for e in sg.find('Step', []):
        print e
        create_or_update_node(e)
    for e in sg.find('HumanUser', [], ('email', 'login', 'name')):
        print e
        create_or_update_node(e)

if True:
    for e in sg.find('Shot', [('project', 'is', {'type': 'Project', 'id': 115})], (
        'sg_sequence',
    )):
        print e
        create_or_update_node(e)

if True:
    for e in sg.find('Task', [('project', 'is', {'type': 'Project', 'id': 115})], (
        'step', 'entity', 'task_assignees'
    )):
        print e
        create_or_update_node(e)






