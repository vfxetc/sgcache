from . import DaemonCommand


class ScannerCommand(DaemonCommand):

    args_sections = ['scanner', 'shotgun', 'core']

    def main(self, args):
        self.cache.scan(
            auto_last_time=self.config['AUTO_LAST_ID'],
            last_time=self.config['SCAN_SINCE'],
            interval=self.config['SCAN_INTERVAL'],
        )
        os._exit(1)


def main():
    ScannerCommand()()
