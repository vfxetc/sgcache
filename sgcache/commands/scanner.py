from . import DaemonCommand


class ScannerCommand(DaemonCommand):

    args_sections = ['scanner', 'shotgun', 'core']

    def add_arguments(self, parser):
        parser.add_argument('-f', '--full', action='store_true',
            help='Force a full scan. Convenience for `--scan-since 0` and `--scan-interval 0`',
        )
        super(ScannerCommand, self).add_arguments(parser)

    def main(self, args):

        controller = self.cache.build_control_server('scanner')

        @controller.register
        def poll(client, msg):
            self.cache.scanner.poll(wait=True)
            return True

        @controller.register
        def start(client, msg):
            return self.cache.scanner.start()

        @controller.register
        def stop(client, msg):
            return self.cache.scanner.stop()

        controller.loop(async=True)

        self.cache.scan(
            auto_last_time=False if args.full else self.config['AUTO_LAST_ID'],
            last_time=0 if args.full else self.config['SCAN_SINCE'],
            interval=0 if args.full else self.config['SCAN_INTERVAL'],
            types=self.config['SCAN_TYPES'],
            projects=self.config['SCAN_PROJECTS'],
        )
        if not args.full:
            # Should never get here.
            os._exit(1)


def main():
    ScannerCommand()()
