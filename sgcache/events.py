import datetime
import logging


log = logging.getLogger(__name__)


class EventProcessor(object):

    def __init__(self, cache):
        self.cache = cache

    def get_handler(self, event):

        if event.domain != 'Shotgun':
            log.info('skipping event; not in Shotgun domain')
            return

        entity_type = self.cache.get(event.entity_type)
        if entity_type is None:
            log.info('skipping event; unknown entity type %s' % event.entity_type)
            return

        func = getattr(self, '_process_%s_event' % event.subtype.lower(), None)
        if func is None:
            log.info('skipping event; unknown event subtype %s' % (event.subtype))
            return

        return lambda con: func(con, event, entity_type)

    def _process_new_event(self, con, event, entity_type):
        '''
        {u'attribute_name': None,
         u'created_at': u'2015-07-09T19:33:37Z',
         u'entity': {u'id': 67378, u'name': u'something', u'type': u'Task'},
         u'event_type': u'Shotgun_Task_New',
         u'id': 2011530,
         u'meta': {u'entity_id': 67378,
                   u'entity_type': u'Task',
                   u'type': u'new_entity'},
         u'project': {u'id': 66, u'name': u'Testing Sandbox', u'type': u'Project'},
         u'type': u'EventLogEntry'}
        '''

        # We need to fetch all of the data from the server; bleh.
        entity = self.cache.event_log.shotgun.find_one(entity_type.type_name,
            filters=[('id', 'is', event.entity_id)],
            fields=[key for key, field in entity_type.fields.iteritems() if field.is_cached()]
        )

        if not entity:
            log.warning('could not find "new" %s %d' % (entity_type.type_name, event.entity_id))
            return

        # We assume that updated_at is pulled in from Shotgun, as it only
        # really matters if we are caching it anyways.

        # Strip our any extra columns Shotgun might have sent us.
        entity = self.cache.filter_cacheable_entity(entity)

        self.cache.create_or_update(entity_type.type_name,
            data=entity,
            create_with_id=True,
            con=con,
            source_event=event,
            extra={
                '_last_log_event_id': event['id'],
                '_active': not event.entity_is_retired,
            },
        )

    def _process_change_event(self, con, event, entity_type):
        '''
        {u'attribute_name': u'color',
         u'created_at': u'2015-07-09T19:33:37Z',
         u'entity': {u'id': 67378, u'name': u'something', u'type': u'Task'},
         u'event_type': u'Shotgun_Task_Change',
         u'id': 2011531,
         u'meta': {u'attribute_name': u'color',
                   u'entity_id': 67378,
                   u'entity_type': u'Task',
                   u'field_data_type': u'color',
                   u'in_create': True,
                   u'new_value': u'pipeline_step',
                   u'old_value': None,
                   u'type': u'attribute_change'},
         u'project': {u'id': 66, u'name': u'Testing Sandbox', u'type': u'Project'},
         u'type': u'EventLogEntry'}

        OR (on a backref)

        {
            "attribute_name": "tasks", 
            "created_at": "2015-07-09T23:00:10Z", 
            "entity": {
                "id": 7080, 
                "name": "002_001", 
                "type": "Shot"
            }, 
            "event_type": "Shotgun_Shot_Change", 
            "id": 2011759, 
            "meta": {
                "actual_attribute_changed": "Task.entity", 
                "added": [
                    {
                        "id": 67380, 
                        "name": "newtask3", 
                        "status": "wtg", 
                        "type": "Task", 
                        "uuid": "3fc23e92-268e-11e5-ac19-0025900054a4", 
                        "valid": "valid"
                    }
                ], 
                "attribute_name": "tasks", 
                "entity_id": 67380, 
                "entity_type": "Task", 
                "field_data_type": "entity", 
                "in_create": true, 
                "original_event_log_entry_id": 2011758, 
                "removed": [], 
                "type": "attribute_change"
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry"
        }

        OR (after a retirement; note the NULL entity):

        {
            "attribute_name": "retirement_date", 
            "created_at": "2015-07-13T21:54:01Z", 
            "entity": null, 
            "event_type": "Shotgun_Task_Change", 
            "id": 2017315, 
            "meta": {
                "attribute_name": "retirement_date", 
                "entity_id": 67519, 
                "entity_type": "Task", 
                "new_value": "2015-07-13 21:54:01 UTC", 
                "old_value": null, 
                "type": "attribute_change"
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry", 
            "user": {
                "id": 108, 
                "name": "Mike Boers", 
                "type": "HumanUser"
            }
        }

        BUT:

            >>> sg.find_one('Task', [('$FROM$EventLogEntry.entity.id', 'is', 2017315)], [], retired_only=True)
            {'type': 'Task', 'id': 67519}


        '''

        # Make sure it is a field we care about.
        try:
            field = self.cache[event.entity_type][event['attribute_name']]
        except KeyError:
            return
        if not field.is_cached():
            return

        # This could be a retired entity, in which case we just need the ID.
        data = event.entity.copy() if event.entity else {'type': event.entity_type, 'id': event.entity_id}

        if event.get('project'):
            data.setdefault('project', event['project'])

        # Use an internal syntax for adding or removing from multi-entities.
        added = event.meta.get('added')
        removed = event.meta.get('removed')
        if added or removed:
            data[event['attribute_name']] = {'__added__': added, '__removed__': removed}
        else:
            data[event['attribute_name']] = event['meta']['new_value']

        # Pull in the updated_at (assuming that it is cached, of course).
        data.setdefault('updated_at', event.get('entity.%s.updated_at' % event.entity_type))

        data = self.cache.filter_cacheable_entity(data)
        
        handler = self.cache.create_or_update(entity_type.type_name,
            data=data,
            create_with_id=True,
            con=con,
            source_event=event,
            extra={
                '_last_log_event_id': event['id'],
            },
        )

        # If we did not know about it, then fetch all data as if it is new.
        if not handler.entity_exists:
            log.warning('updated un-cached %s %s; fetching all data' % (event.entity_type, event.entity_id))
            self._process_new_event(con, event, entity_type)

    def _process_retirement_event(self, con, event, entity_type):
        '''
        {
            "attribute_name": null, 
            "created_at": "2015-07-13T22:32:35Z", 
            "entity": null, 
            "event_type": "Shotgun_Task_Retirement", 
            "id": 2017525, 
            "meta": {
                "class_name": "Task", 
                "display_name": "another to delete", 
                "entity_id": 67531, 
                "entity_type": "Task", 
                "id": 67531, 
                "retirement_date": "2015-07-13 22:32:35 UTC", 
                "type": "entity_retirement"
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry", 
            "user": {
                "id": 108, 
                "name": "Mike Boers", 
                "type": "HumanUser"
            }
        }
        '''

        if not self.cache.retire(event.entity_type, event.entity_id, con=con, source_event=event, strict=False):
            log.warning('retired un-cached %s %s; ignoring' % (event.entity_type, event.entity_id))

    def _process_revival_event(self, con, event, entity_type):
        '''
        {
            "attribute_name": null, 
            "created_at": "2015-07-13T22:34:21Z", 
            "entity": {
                "id": 67531, 
                "name": "another to delete", 
                "type": "Task"
            }, 
            "event_type": "Shotgun_Task_Revival", 
            "id": 2017561, 
            "meta": {
                "class_name": "Task", 
                "display_name": "another to delete", 
                "entity_id": 67531, 
                "entity_type": "Task", 
                "id": 67531
            }, 
            "project": {
                "id": 66, 
                "name": "Testing Sandbox", 
                "type": "Project"
            }, 
            "type": "EventLogEntry", 
            "user": {
                "id": 108, 
                "name": "Mike Boers", 
                "type": "HumanUser"
            }
        }
        '''

        # Pull in updated_at.
        extra = {}
        updated_at = event.get('entity.%s.updated_at' % event.entity_type)
        if updated_at:
            extra['updated_at'] = updated_at

        if not self.cache.revive(event.entity_type, event.entity_id, con=con, source_event=event, extra=extra, strict=False):
            log.warning('revived un-cached %s %d; processing as new' % (event.entity_type, entity_id))
            self._process_new_event(con, event, entity_type)


