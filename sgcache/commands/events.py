from . import DaemonCommand


class EventsCommand(DaemonCommand):

    args_sections = ['events', 'shotgun', 'core']

    def main(self, args):
        self.cache.watch(
            auto_last_id=self.config['AUTO_LAST_ID'],
            idle_delay=self.config['WATCH_IDLE_DELAY'],
        )
        os._exit(1)


def main():
    EventsCommand()()
