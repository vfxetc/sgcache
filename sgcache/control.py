import errno
import functools
import json
import logging
import os
import socket
import threading
import time
import traceback


log = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, addr):
        self.addr = addr
        self.handlers = {}

    def register(self, func=None, **kwargs):
        if func is None:
            return functools(self.register(**kwargs))
        self.handlers[kwargs.get('name') or func.__name__] = func

    def loop(self, async=False):

        if async:
            thread = threading.Thread(target=self.loop)
            thread.daemon = True
            thread.start()
            return thread

        while True:
            try:

                if isinstance(self.addr, basestring):
                    try:
                        os.unlink(self.addr)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise

                ssock = socket.socket(socket.AF_UNIX if isinstance(self.addr, basestring) else socket.AF_INET)
                ssock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                ssock.bind(self.addr)
                ssock.listen(5)
                self._accept(ssock)
            except Exception as e:
                log.exception('error while listening for connections; sleeping for 60s')
                time.sleep(60)

    def _accept(self, ssock):
        while True:
            try:
                csock, addr = ssock.accept()
            except socket.timeout:
                continue
            thread = threading.Thread(target=self._handle_child, args=[csock, addr])
            thread.daemon = True
            thread.start()

    def _handle_child(self, csock, addr):
        try:
            buffer_ = ''
            while True:
                new = csock.recv(4096)
                if not new:
                    return
                buffer_ += new
                if '\n' in buffer_:
                    line, buffer_ = buffer_.split('\n', 1)
                    data = json.loads(line)
                    type_ = data.pop('type')
                    log.info('received %s' % type_)
                    func = self.handlers[type_]
                    res = func(**data)
                    csock.send(json.dumps(res) + '\n')
        except Exception:
            log.warning('exception in control thread:\n' + traceback.format_exc())
        finally:
            try:
                csock.close()
            except:
                pass
