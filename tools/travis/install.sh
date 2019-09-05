#!/bin/bash
# This install script is used by the "install" step defined in travis.yml
# See https://docs.travis-ci.com/user/installing-dependencies/

# Install the requirements.
pip install --upgrade -r pip-req.txt
pip install --upgrade https://github.com/PyCQA/pylint/archive/master.zip

#download nltk data packages
python -c "import nltk; nltk.download('all')" || echo "NLTK data download failed: $?"

# speed up the compilation of cythonized C extensions by instructing distutils to use multiple cores
# travis jobs have two cores available, see
# https://docs.travis-ci.com/user/reference/overview/#virtualisation-environment-vs-operating-system
printf '[build_ext]\nparallel=3' > ~/.pydistutils.cfg
