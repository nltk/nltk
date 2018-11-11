#!/bin/bash
# This install script is used by the "install" step defined in travis.yml
# See https://docs.travis-ci.com/user/installing-dependencies/

set -x # Print all executed commands to the terminal.

# Set JAVA env variable.
JAVA_HOME=/opt/jdk/jdk8.latest/bin

# Checking Java and Python version.
java -version
python --version

# Which Python / pip
which python
which pip
pip -V
