from sgcache.web.core import schema, app

# Watch the event log in a thread.
schema.watch(async=True)

app.run(debug=True, port=8000)
