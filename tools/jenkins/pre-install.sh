#!/bin/bash
# This install script is pre-installation environment setup for old jenkins CI:
# https://nltk.ci.cloudbees.com/job/pull_request_tests/configure

set -e # Exit immediately if a command exits with a non-zero status.
set -x # Print all executed commands to the terminal.

# The following are from Jenkins "Build Environment > Properties Content":
# https://nltk.ci.cloudbees.com/job/pull_request_tests/configure
PATH=$PATH:/scratch/jenkins/python/python-3.5.4-x86_64/bin
PATH=$PATH:/scratch/jenkins/python/python-3.6.4-x86_64/bin

PATH=$PATH:/opt/local/bin:/opt/local/sbin
PATH=$PATH:/usr/bin:/bin:/usr/sbin
PATH=$PATH:/s # Heh? Not sure why does this exist in CI?? Leaving it here first.
PATH=$PATH:/usr/local/bin

JAVA_HOME=/opt/jdk/jdk8.latest/bin
BLAS=/home/jenkins/lib/
LAPACK=/home/jenkins/lib/

# Checking Java and Python version.
java -version
python --version


# More Jenkins related commands from "Build Environment > Script Content":
# https://nltk.ci.cloudbees.com/job/pull_request_tests/configure
curl -s -o use-python https://repository-cloudbees.forge.cloudbees.com/distributions/ci-addons/python/use-python
chmod u+x use-python
export PYTHON_VERSION=${PYV}
. ./use-python

mkdir -p /home/jenkins/lib
[ -f /home/jenkins/lib/libblas.so ] || ln -sf /usr/lib64/libblas.so.3 /home/jenkins/lib/libblas.so
[ -f /home/jenkins/lib/liblapack.so ] || ln -sf /usr/lib64/liblapack.so.3 /home/jenkins/lib/liblapack.so
