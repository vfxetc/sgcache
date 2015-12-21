import sys

from . import DaemonCommand
from ..web.core import make_app

try:
    from gunicorn.app.base import BaseApplication
except ImportError:
    BaseApplication = object


class GunicornRunner(BaseApplication):

    def __init__(self, command):
        self.__command = command
        super(GunicornRunner, self).__init__(self)

    def load_config(self):

        self.cfg.set('bind', '0.0.0.0:%s' % self.__command.config['PORT'])
        
        def post_fork(server, worker):
            self.__command.log.info('Post-fork cleanup.')
            self.__command.cache.db.dispose()

        # Need to reset engine pools.
        self.cfg.set('post_fork', post_fork)

        for k, v in self.__command.config.__dict__.iteritems():
            if k.startswith('GUNICORN_') and v is not None:
                # This is a bit fragile.
                if isinstance(v, basestring) and v.isdigit():
                    v = int(v)
                self.cfg.set(k[9:].lower(), v)

    def load(self):
        return self.__command.load_app()


class WebCommand(DaemonCommand):

    def __init__(self):
        super(WebCommand, self).__init__()
        self._app = None

    def load_app(self):
        if self._app is None:
            self._app = make_app(cache=self.cache, config=self.config)
        return self._app

    def main(self, args):

        app = self.load_app()
        port = app.config['PORT']

        worker_class = self.config['GUNICORN_WORKER_CLASS']
        if worker_class:

            if BaseApplication is object: # on ImportError
                self.log.error('could not import gunicorn; aborting')
                exit(1)

            self.log.info('starting API proxy via Gunicorn %s on port %s' % (worker_class, port))
            GunicornRunner(self).run()

        # Fall back onto Flask.
        else:
            self.log.info('starting API proxy via Flask server on port %s' % port)
            app.run(port=port)


def main():
    WebCommand()()


