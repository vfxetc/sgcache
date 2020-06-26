
export SGCACHE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd)"

export SGCACHE_VENV="$SGCACHE_ROOT/venv"

# Make a virtual environment for Python packages.
if [[ ! -f "$SGCACHE_VENV/bin/activate" ]]; then
    virtualenv -p python2 "$SGCACHE_VENV"
    if [[ $? != 0 ]]; then
        echo "Could not create virtualenv."
        return
    fi
fi
source "$SGCACHE_VENV/bin/activate"


export SGCACHE_CONFIG="$SGCACHE_ROOT/var/config.py"
