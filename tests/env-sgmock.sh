
# Source this file to setup a sane SGCache testing environment.

unset SGCACHE_CONFIG

export SGCACHE_SHOTGUN_URL='http://127.0.0.1:8020' # sgmock
export SGCACHE_SCHEMA='tests/schema-basic.yml'
export SGCACHE_SQLA_URL='postgres:///sgcache-mock'
export SGCACHE_TESTING='1'

