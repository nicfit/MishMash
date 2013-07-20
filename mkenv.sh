#!/bin/bash

_PYTHON=${2:-python2.7}
_PYTHON_VERSION=$($_PYTHON -c 'import sys; print(".".join([str(v) for v in sys.version_info[:2]]))')
_ENV=${1:-mishmash-${_PYTHON_VERSION}}

source /usr/bin/virtualenvwrapper.sh

mkvirtualenv -a $(pwd) --python=${_PYTHON} --distribute ${_ENV}
workon $_ENV

PKGS_OPTS=
if test -d ./.pip-download-cache; then
    export PIP_DOWNLOAD_CACHE=./.pip-download-cache
fi

pip install $PKG_OPTS -r requirements.txt

cat /dev/null >| $VIRTUAL_ENV/bin/postactivate
echo "alias cd-top=\"cd $PWD\"" >> $VIRTUAL_ENV/bin/postactivate
echo "alias mishmash=\"eyeD3 --plugin=mishmash\"
echo "export PATH=\"$PWD/bin:$PATH\"" >> $VIRTUAL_ENV/bin/postactivate
echo "export PYTHONPATH=\"$PWD/src\"" >> $VIRTUAL_ENV/bin/postactivate

cat /dev/null >| $VIRTUAL_ENV/bin/postdeactivate
echo "unalias cd-top" >> $VIRTUAL_ENV/bin/postdeactivate
echo "unset PYTHONPATH" >> $VIRTUAL_ENV/bin/postdeactivate
