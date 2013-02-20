#! /bin/sh

ROOT=`dirname $0`

$ROOT/pip-install.py
coverage erase
coverage run $ROOT/nltk/test/runtests.py --with-xunit
coverage xml
iconv -c -f utf-8 -t utf-8 nosetests.xml > nosetests_scrubbed.xml
pylint -f parseable $ROOT/nltk > pylintoutput
true   # script always succeeds
