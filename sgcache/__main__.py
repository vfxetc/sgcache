import os
import logging

log = logging.getLogger('sgcache.main')


from sgcache import config

config.update_from_argv()

# Import after config.
from sgcache.web.core import schema, app

# Watch the event log in a thread.
if app.config['WATCH_EVENTS']:
    log.info('starting event watcher')
    schema.watch(async=True, auto_last_id=app.config['AUTO_LAST_ID'])
else:
    log.warning('not watching events!')

if app.config['SCAN_SINCE'] or app.config['SCAN_INTERVAL']:
    log.info('starting scanner')
    schema.scan(async=True, last_time=app.config['SCAN_SINCE'] or app.config['SCAN_INTERVAL'], interval=app.config['SCAN_INTERVAL'])
else:
    log.warning('not starting scanner!')

port = int(os.environ.get('PORT', config.PORT))
log.info('starting web server on port %s' % port)

app.run(port=port)

