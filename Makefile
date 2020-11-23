# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2020 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#	 Edward Loper <edloper@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

PYTHON = python
VERSION = $(shell $(PYTHON) -c 'import nltk; print(nltk.__version__)' | sed '/^Warning: */d')
NLTK_URL = $(shell $(PYTHON) -c 'import nltk; print(nltk.__url__)' | sed '/^Warning: */d')

.PHONY: all clean clean_code

all: dist

########################################################################
# TESTING
########################################################################
DOCTEST_FILES = nltk/test/*.doctest
DOCTEST_CODE_FILES = nltk/*.py nltk/*/*.py

doctest:
	pytest $(DOCTEST_FILES)

doctest_code:
	pytest $(DOCTEST_CODE_FILES)

demotest:
	find nltk -name "*.py"\
        -and -not -path *misc* \
        -and -not -name brown_ic.py \
        -exec echo ==== '{}' ==== \; -exec python '{}' \;

########################################################################
# DISTRIBUTIONS
########################################################################

dist: zipdist

# twine only permits one source distribution
#gztardist: clean_code
#	$(PYTHON) setup.py -q sdist --format=gztar
zipdist: clean_code
	$(PYTHON) setup.py -q sdist --format=zip bdist_wheel
windist: clean_code
	$(PYTHON) setup.py -q bdist --format=wininst --plat-name=win32

########################################################################
# CLEAN
########################################################################

clean: clean_code
	rm -rf build iso dist api MANIFEST nltk-$(VERSION) nltk.egg-info

clean_code:
	rm -f `find nltk -name '*.pyc'`
	rm -f `find nltk -name '*.pyo'`
	rm -f `find . -name '*~'`
	rm -f MANIFEST # regenerate manifest from MANIFEST.in
