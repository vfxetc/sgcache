import logging

import sqlalchemy as sa

from sgcache.schema.core import Schema
from sgcache.schema.read import ReadRequest


# disable our loggers
logging.getLogger(None).handlers = []


db = sa.create_engine('sqlite://', echo=True)


schema = Schema(db)

shot_id = db.execute(schema['Shot'].table.insert().values(name='AA_001')).inserted_primary_key[0]
task_id = db.execute(schema['Task'].table.insert().values(content='Animate', entity__type='Shot', entity__id=shot_id)).inserted_primary_key[0]

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
            }
        ], 
        "logical_operator": "and"
    }, 
    "paging": {
        "current_page": 1, 
        "entities_per_page": 1
    }, 
    "return_fields": [
        "id",
        #"content",
        "entity",
        #"entity.Shot.name",
    ], 
    "return_only": "active", 
    "return_paging_info": False, 
    "type": "Task"
}

req = ReadRequest(raw_request)
res = req(schema)

print res
