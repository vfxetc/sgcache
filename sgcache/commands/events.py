from . import DaemonCommand

class EventsCommand(DaemonCommand):

    args_sections = ['events', 'shotgun', 'core']

    def main(self, args):

        controller = self.cache.build_control_server('events')
        @controller.register
        def wake_up(client, msg):
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
