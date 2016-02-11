import sys

from . import DaemonCommand

class ControlCommand(DaemonCommand):

    args_sections = ['core']

    def add_arguments(self, parser):
        parser.add_argument('-t', '--timeout', type=float, default=5.0)
        parser.add_argument('service')
        parser.add_argument('type')
        super(ControlCommand, self).add_arguments(parser)

    def main(self, args):

        client = self.cache.get_control_client(args.service)
        if args.type == 'ping':
            pong = client.ping(timeout=args.timeout)
            print pong['pid']
            return

        else:
            print >> sys.stderr, 'unknown control type', repr(args.type)
            return 1


def main():
    exit(ControlCommand()() or 0)
