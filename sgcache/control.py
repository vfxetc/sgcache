from __future__ import absolute_import

from select import select
import errno
import functools
import itertools
import json
import logging
import os
import socket
import threading
import time
import traceback

log = logging.getLogger(__name__)


from .utils import makedirs, unlink


class TimeOut(Exception):
    pass

base_handlers = {
    'ping': lambda control, msg: {'type': 'pong', 'pid': os.getpid()}
}

def _coerce_msg(type=None, **msg):

    if type:
        if isinstance(type, basestring):
            msg['type'] = type
            return msg
        elif msg:
            raise ValueError('cannot specify dict message and kwargs')
        else:
            msg = dict(type)

    if 'type' not in msg:
        raise ValueError('message requires type')
    return msg


class ControlClient(object):

    handlers = base_handlers.copy()

    def __init__(self, addr=None, sock=None, server=None):

        self.addr = addr
        self.sock = sock
        self.server = server

        self._line_buffer = ''
        self._message_buffer = []
        self._handler_reply_ids = None
        self._session_generator = itertools.count(1)

        if sock is None:
            self.connect()

    def connect(self):

        # This is indempodent.
        if self.sock is not None:
            return

        if self.addr is None:
            return

        if isinstance(self.addr, basestring):
            self.sock = socket.socket(socket.AF_UNIX)
        else:
            self.sock = socket.socket(socket.AF_INET)
        self.sock.connect(self.addr)

        return True

    def close(self):
        if self.sock:
            self.sock.close()
        self.sock = None

    def _readline(self, timeout=None):

        if not self.sock:
            return

        if timeout:
            end_time = time.time() + timeout

        buffer_ = self._line_buffer
        while True:

            r, _, _ = select([self.sock], [], [], max(0, end_time - time.time()) if timeout else None)
            if not r:
                raise TimeOut()

            new = self.sock.recv(4096)
            if not new:
                self.sock = None
                self._line_buffer = ''
                return

            buffer_ += new
            if '\n' in buffer_:
                line, buffer_ = buffer_.split('\n', 1)
                self._line_buffer = buffer_
                return line

    def recv(self, timeout=None):
        try:
            return self._message_buffer.pop(0)
        except IndexError:
            pass
        for attempt_num in (0, 1):
            self.connect()
            try:
                line = self._readline(timeout)
            except socket.error as e:
                if attempt_num:
                    raise
            if line:
                try:
                    return json.loads(line)
                except:
                    self.send('error', message='malformed message')
                    self.close()
                    return
            if attempt_num:
                return

    def recv_for(self, wait_id, timeout=None):
        for i in xrange(len(self._message_buffer)):
            msg = self._message_buffer[i]
            if msg.get('for') == wait_id:
                self._message_buffer.pop(i)
                return msg
        while True:
            msg = self.recv(timeout)
            if not msg:
                return
            if msg.get('for') == wait_id:
                return msg
            self._message_buffer.append(msg)

    def send(self, *args, **kwargs):

        msg = _coerce_msg(*args, **kwargs)

        wait_id = msg.get('wait')
        if wait_id is True:
            wait_id = msg['wait'] = next(self._session_generator)

        encoded = json.dumps(msg)

        # Track what has been sent automatically.
        if wait_id is not None and self._handler_reply_ids is not None:
            self._handler_reply_ids.add(wait_id)

        # Attempt to reconnect a couple times when sending this.
        for attempt_num in (0, 1):
            self.connect()
            try:
                self.sock.send(encoded + '\n')
            except socket.error as e:
                if attempt_num:
                    raise
            return wait_id

    def reply_to(self, original, *args, **kwargs):
        wait_id = original.get('wait')
        if wait_id is None:
            raise ValueError('original message has no session')
        msg = _coerce_msg(*args, **kwargs)
        msg['for'] = wait_id
        self.send(msg)

    def send_and_recv(self, type, **kwargs):
        timeout = kwargs.pop('timeout')
        msg = _coerce_msg(type, **kwargs)
        msg['wait'] = True
        wait_id = self.send(msg)
        return self.recv_for(wait_id, timeout)

    def ping(self, timeout=None):
        return self.send_and_recv('ping', pid=os.getpid(), timeout=timeout)

    def loop(self, async=False):

        if async:
            thread = threading.Thread(target=self.loop)
            thread.daemon = True
            thread.start()
            return thread

        while True:

            msg = self.recv()
            if not msg:
                return

            type_ = msg.get('type')
            wait_id = msg.get('wait')

            func = self.handlers.get(type_)
            if func is None and self.server:
                func = self.server.handlers.get(type_)
            if func is None:
                log.warning('unknown message type %r' % type_)
                self.reply_to(msg, 'error', message='unknown message type %r' % type_)
                continue

            if self.server and self.server.name:
                log.info('%s handling %s' % (self.server.name, type_))
            else:
                log.info('handling %s' % type_)

            self._handler_reply_ids = set()
            try:
                res = func(self, msg)
            except Exception as e:
                self.reply_to(msg, 'error', message='unhandled exception %s' % e)
                continue

            # If the handler replied, then we are done.
            if res is None and wait_id is None or wait_id in self._handler_reply_ids:
                continue

            res = res.copy() if isinstance(res, dict) and 'type' in res else {'type': 'result', 'value': res}
            if wait_id is not None:
                res['for'] = wait_id
            self.send(res)




class ControlServer(object):

    def __init__(self, addr, name=None):

        self.addr = addr
        self.name = name
        self.handlers = base_handlers.copy()

        if isinstance(self.addr, basestring):
            self.sock = socket.socket(socket.AF_UNIX)
            if os.path.exists(self.addr):
                # TODO: Try connecting to it before destroying it.
                unlink(self.addr)
            makedirs(os.path.dirname(self.addr))
        else:
            self.sock = socket.socket(socket.AF_INET)

        self.sock.bind(self.addr)
        self.sock.listen(5)

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
                client_sock, addr = self.sock.accept()
            except socket.timeout:
                continue

            client = ControlClient(sock=client_sock, server=self)
            client.loop(async=True)
