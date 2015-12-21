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
        log.info('Started child %s:%s (%d)' % (module_name, func_name, pid))
        return pid

    # We cannot allow control to return to the parent.
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

        pid = call_in_child('sgcache.commands.events')
        pids[pid] = 'events'

        pid = call_in_child('sgcache.commands.scanner')
        pids[pid] = 'scanner'

        pid = call_in_child('sgcache.commands.web')
        pids[pid] = 'web'

        log.debug('Waiting on children')
        pid, code = os.wait()

        log.error('Child sgcache-%s (%s) exited with code %d' % (pids.pop(pid), pid, code))

    except:
        code = 100

    finally:

        # Ask them to stop.
        for pid, name in sorted(pids.iteritems()):
            log.info('Stopping sgcache-%s (%d)' % (name, pid))
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as e:
                if e.errno != errno.ESRCH: # Process does not exist
                    raise

        # Give them a second...
        time.sleep(1)

        # Force them to stop.
        for pid, name in sorted(pids.iteritems()):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError as e:
                if e.errno != errno.ESRCH: # Process does not exist
                    raise

    os._exit(code)
