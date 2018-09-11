#!/usr/bin/env bash

set -e # Exit immediately if a command exits with a non-zero status.
set -x # Print all executed commands to the terminal.

# Sanity check on sklearn
python -c "import sklearn; print(sklearn.__version__)"
python -c "import matplotlib as plt; print(plt.__version__)"

echo "$(pwd)"  # Know which directory tox is running this shell from.

#coverage
coverage erase
coverage run --source=nltk $(pwd)/runtests.py -v --with-xunit
coverage xml --omit=$(pwd)/test/*
iconv -c -f utf-8 -t utf-8 nosetests.xml > nosetests_scrubbed.xml

# Create a default pylint configuration file.
touch $HOME/.pylintrc
pylint -f parseable nltk > $(pwd)/pylintoutput

#script always succeeds
true
