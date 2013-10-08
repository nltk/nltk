#! /bin/sh

cd `dirname $0`

python -c "import nltk; nltk.download('all')" || echo "NLTK data download failed: $?"
./pip-install.py
coverage erase
coverage run --source=nltk nltk/test/runtests.py --with-xunit
coverage xml --omit=nltk/test/*
iconv -c -f utf-8 -t utf-8 nosetests.xml > nosetests_scrubbed.xml
pylint -f parseable nltk > pylintoutput
true   # script always succeeds
