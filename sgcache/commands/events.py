from . import DaemonCommand
from ..control import Controller

class EventsCommand(DaemonCommand):

    args_sections = ['events', 'shotgun', 'core']

    def main(self, args):

        controller = Controller(self.cache.config['SOCKET_PATH'] % 'events')
        @controller.register
        def wake_up(**kw):
            self.cache.event_log.wake_up(wait=True)
            return True
        controller.loop(async=True)

        self.cache.watch(
            auto_last_id=self.config['AUTO_LAST_ID'],
            idle_delay=self.config['WATCH_IDLE_DELAY'],
        )
        os._exit(1)


def main():
    EventsCommand()()
