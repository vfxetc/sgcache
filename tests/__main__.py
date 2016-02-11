import os

from . import connect


sg = connect(os.environ.get('SGCACHE_SHOTGUN_URL', 'http://localhost:8020/'))
cache = connect()
