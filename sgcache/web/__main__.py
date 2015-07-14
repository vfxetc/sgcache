from sgcache.web.core import schema, app

# Watch the event log in a thread.
if app.config['WATCH_EVENTS']:
    schema.watch(async=True, auto_last_id=app.config['AUTO_LAST_ID'])

app.run(port=8000)
