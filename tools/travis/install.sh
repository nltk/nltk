#!/bin/bash
# This install script is used by the "install" step defined in travis.yml
# See https://docs.travis-ci.com/user/installing-dependencies/

# Install the requirements.
pip install --upgrade -r pip-req.txt
pip install --upgrade https://github.com/PyCQA/pylint/archive/master.zip

#download nltk data packages
python -c "import nltk; nltk.download('all', force=True)" || echo "NLTK data download failed: $?"
