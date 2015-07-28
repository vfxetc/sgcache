import os
import logging

log = logging.getLogger('sgcache.main')


from sgcache import config

config.update_from_argv()

# Must import app after config.
from sgcache.web.core import cache, app

threads = []

# Watch the event log in a thread.
if app.config['WATCH_EVENTS']:
    log.info('starting event watcher')
    threads.append(cache.watch(
        async=True,
        auto_last_id=app.config['AUTO_LAST_ID'],
        idle_delay=float(app.config['WATCH_IDLE_DELAY']),
    ))
else:
    log.warning('not watching events!')

# Scan for updates in a thread.
if app.config['SCAN_SINCE'] or app.config['SCAN_INTERVAL']:
    log.info('starting scanner')
    threads.append(cache.scan(
        async=True,
        last_time=app.config['SCAN_SINCE'] or app.config['SCAN_INTERVAL'],
        interval=app.config['SCAN_INTERVAL'],
    ))
else:
    log.warning('not starting scanner!')


port = int(config.PORT)
if port:

    # Use Gunicorn?
    worker_class = config.GUNICORN_WORKER_CLASS
    if worker_class:

        from gunicorn.app.base import BaseApplication
        class Runner(BaseApplication):

            def load_config(self):
                self.cfg.set('bind', '0.0.0.0:%s' % port)
                for k, v in config.__dict__.iteritems():
                    if k.startswith('GUNICORN_') and v is not None:
                        # This is a bit fragile.
                        if isinstance(v, basestring) and v.isdigit():
                            v = int(v)
                        self.cfg.set(k[9:].lower(), v)

            def load(self):
                return app

        log.info('starting API proxy via Gunicorn %s on port %s' % (worker_class, port))
        Runner().run()

    # Fall back onto Flask.
    else:
        log.info('starting API proxy via Flask server on port %s' % port)
        app.run(port=port)

else:
    log.warning('not starting API proxy!')
    for thread in threads:
        thread.join()


