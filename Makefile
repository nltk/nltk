# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#	 Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

PYTHON = python
VERSION = $(shell $(PYTHON) -c 'import nltk; print nltk.__version__' | sed '/^Warning: */d')
NLTK_URL = $(shell $(PYTHON) -c 'import nltk; print nltk.__url__' | sed '/^Warning: */d')

.PHONY: all clean clean_code

all: dist

########################################################################
# TESTING
########################################################################

DOCTEST_DRIVER = nltk/test/doctest_driver.py
DOCTEST_FLAGS = --ellipsis --normalize_whitespace
DOCTEST_FILES = nltk/test/*.doctest
DOCTEST_CODE_FILES = nltk/*.py nltk/*/*.py

doctest:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_FLAGS) $(DOCTEST_FILES)

doctest_code:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_FLAGS) $(DOCTEST_CODE_FILES)

demotest:
	find nltk -name "*.py"\
        -and -not -path *misc* \
        -and -not -name brown_ic.py \
        -exec echo ==== '{}' ==== \; -exec python '{}' \;

########################################################################
# JAVA
########################################################################

jar: nltk/nltk.jar

JAVA_SRC = $(shell find javasrc/org/nltk -name '*.java')
nltk/nltk.jar: $(JAVA_SRC)
	$(MAKE) -C javasrc jar
	cp javasrc/nltk.jar nltk/nltk.jar

########################################################################
# DISTRIBUTIONS
########################################################################

dist: zipdist gztardist windist

gztardist: clean_code
	$(PYTHON) setup.py -q sdist --format=gztar
zipdist: clean_code
	$(PYTHON) setup.py -q sdist --format=zip
windist: clean_code
	$(PYTHON) setup.py -q bdist --format=wininst --plat-name=win32

########################################################################
# CLEAN
########################################################################

clean: clean_code
	rm -rf build iso dist api MANIFEST nltk-$(VERSION) nltk.egg-info
	$(MAKE) -C javasrc clean
#	rm -f nltk/nltk.jar

clean_code:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	rm -f `find . -name '*~'`
	rm -f MANIFEST # regenerate manifest from MANIFEST.in
