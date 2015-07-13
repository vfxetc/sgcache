from sgcache.web.core import schema, app

# Watch the event log in a thread.
schema.watch(async=True)

app.run(port=8000)
