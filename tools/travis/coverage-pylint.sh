#!/usr/bin/env bash

set -e # Exit immediately if a command exits with a non-zero status.
set -x # Print all executed commands to the terminal.

# Paranoid checks.
# Checking Java and Python version.
java -version
python --version

# Which Python / pip
which python
which pip
pip -V

echo "$(pwd)"  # Know which directory tox is running this shell from.

#coverage
rm -f coverage_scrubbed.xml
pytest --cov=nltk --cov-report xml
iconv -c -f utf-8 -t utf-8 coverage.xml > coverage_scrubbed.xml

# Create a default pylint configuration file.
##touch $HOME/.pylintrc
##pylint -f parseable nltk > pylintoutput

#script always succeeds
true
