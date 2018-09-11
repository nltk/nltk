#!/usr/bin/env bash

set -e # Exit immediately if a command exits with a non-zero status.
set -x # Print all executed commands to the terminal.

# Check python versions
python --version

#coverage
coverage erase
coverage run --source=nltk $HOME/build/nltk/nltk/test/runtests.py -v --with-xunit
coverage xml --omit=$HOME/build/nltk/nltk/test/*
iconv -c -f utf-8 -t utf-8 nosetests.xml > nosetests_scrubbed.xml

# Create a default pylint configuration file.
touch $HOME/.pylintrc
pylint -f parseable nltk > $HOME/build/pylintoutput

#script always succeeds
true
