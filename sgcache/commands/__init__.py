import argparse
import socket
import logging
import sys

from ..cache import Cache
from ..config import Config
from ..logs import setup_logs


class DaemonCommand(object):

    args_sections = ['core', 'shotgun']

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.config = Config()

        self.add_arguments(self.parser)

        self.log = logging.getLogger(self.__class__.__module__)

    def add_arguments(self, parser):
        self.config.add_arguments(self.parser, self.args_sections)

    def load_app(self):
        pass

    def main(self, args):
        raise NotImplementedError()

    def __call__(self, argv=None):

        args = self.parser.parse_args(argv)
        self.config.parse_args(args)

        self.cache = Cache(config=self.config)

        # Setup logging *after* SQLA so that it can deal with its handlers.
        setup_logs(self.load_app())

        # Set a global socket timeout, so that nothing socket related will ever
        # lock us up. This is likely to cause a few extra problems, but we can
        # deal with them.
        socket.setdefaulttimeout(60.1)

        ret = self.main(args) or 0
        exit(ret)
