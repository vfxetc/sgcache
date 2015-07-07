import logging

import sqlalchemy as sa
import yaml
from sgcache.schema.core import Schema
from sgcache.apimethods.read import ReadHandler


# disable our loggers
logging.getLogger(None).handlers = []


db = sa.create_engine('sqlite://', echo=True)

schema_spec = yaml.load(open('schema/keystone-basic.yml').read())
schema = Schema(db, schema_spec)

project_id = db.execute(schema['Project'].table.insert().values(code='PROJECT')).inserted_primary_key[0]
sequence_id = db.execute(schema['Sequence'].table.insert().values(code='AA', project__type='Project', project__id=project_id)).inserted_primary_key[0]
shot_id = db.execute(schema['Shot'].table.insert().values(code='AA_001', sg_sequence__type='Sequence', sg_sequence__id=sequence_id)).inserted_primary_key[0]
task_id = db.execute(schema['Task'].table.insert().values(content='Animate', entity__type='Shot', entity__id=shot_id)).inserted_primary_key[0]

user1_id = db.execute(schema['HumanUser'].table.insert().values(name='Alice')).inserted_primary_key[0]
user2_id = db.execute(schema['HumanUser'].table.insert().values(name='Bob')).inserted_primary_key[0]
db.execute(schema['Task']['task_assignees'].assoc_table.insert().values(parent_id=task_id, child_type='HumanUser', child_id=user1_id))
db.execute(schema['Task']['task_assignees'].assoc_table.insert().values(parent_id=task_id, child_type='HumanUser', child_id=user2_id))

#print db.execute('select shot.id from shot').fetchall()
#print db.execute('select task.id, task.entity__id from task').fetchall()
#print db.execute('select task.id, shot.id from task join shot on task.entity__id = shot.id').fetchall()
#exit()

raw_request = {
    "api_return_image_urls": True, 
    "filters": {
        "conditions": [
            {
                "path": "entity.Shot.id", 
                "relation": "is", 
                "values": [shot_id]
            },
            {
                "path": "content", 
                "relation": "is", 
                "values": ["Animate"]
            },
            {
                "path": "entity.Shot.sg_sequence.Sequence.code", 
                "relation": "in", 
                "values": ["AA", "BB"]
            },
        ], 
        "logical_operator": "and"
    }, 
    "paging": {
        "current_page": 1, 
        "entities_per_page": 1
    }, 
    "return_fields": [
        #"id",
        #"content",
        #"entity",
        #"entity.Shot.name",
        "task_assignees",
        "entity.Shot.sg_sequence.Sequence.project.Project.code",
    ], 
    "return_only": "active", 
    "return_paging_info": False, 
    "type": "Task"
}

req = ReadHandler(raw_request)
res = req(schema)

print res
