import sys
import json

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
            res = client.send(args.type)
            if res:
                print json.dumps(res, indent=4, sort_keys=True)



def main():
    exit(ControlCommand()() or 0)
