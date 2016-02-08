from . import DaemonCommand


class ScannerCommand(DaemonCommand):

    args_sections = ['scanner', 'shotgun', 'core']

    def add_arguments(self, parser):
        parser.add_argument('-f', '--full', action='store_true',
            help='Force a full scan. Convenience for `--scan-since 0` and `--scan-interval 0`',
        )
        super(ScannerCommand, self).add_arguments(parser)

    def main(self, args):
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
