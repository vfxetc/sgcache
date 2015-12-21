import os
import logging
import signal
import time
import errno
import traceback
from ..logs import setup_logs

log = logging.getLogger(__name__)


def call_in_child(module_name, func_name='main'):
    
    pid = os.fork()
    if pid:
        return pid

    try:
        module = __import__(module_name, fromlist=['.'])
        func = getattr(module, func_name)
        func()
    except Exception:
        traceback.print_exc()
    finally:
        os._exit(1)


def main():

    setup_logs()

    pids = {}

    try:

        log.info('Starting event watcher...')
        pid = call_in_child('sgcache.commands.events')
        pids[pid] = 'events'

        log.info('Starting scanner...')
        pid = call_in_child('sgcache.commands.scanner')
        pids[pid] = 'scanner'

        log.info('Starting web server...')
        pid = call_in_child('sgcache.commands.web')
        pids[pid] = 'web'

        log.info('Waiting on children...')
        time.sleep(1)
        pid, code = os.wait()
        log.error('Child %d (%s) exited with code %d' % (pid, pids.pop(pid), code))

    except:
        code = 100

    finally:
        for pid, name in sorted(pids.iteritems()):
            log.info('Killing %s (%d)...' % (name, pid))
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
                os.kill(pid, signal.SIGKILL)
            except OSError as e:
                if e.errno != errno.ESRCH: # Process does not exist
                    raise

    os._exit(code)
