#!/bin/bash
# This install script is used by the "install" step defined in travis.yml
# See https://docs.travis-ci.com/user/installing-dependencies/

# Install the requirements.
pip install --upgrade -r pip-req.txt
pip install --upgrade https://github.com/PyCQA/pylint/archive/master.zip

#download nltk data packages
python -c "import nltk; nltk.download('all')" || echo "NLTK data download failed: $?"

# Paranoid checks.
# Checking Java and Python version.
java -version
python --version

# Which Python / pip
which python
which pip
pip -V

# Sanity check on sklearn
python -c "import sklearn; print(sklearn.__version__)"
python -c "import matplotlib as plt; print(plt.__version__)"
