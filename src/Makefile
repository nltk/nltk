# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

TESTS = token tree probability set


all: distributions

# Tests.  Run each test with Python.
TESTS_PY := $(TESTS:=.py)
test: $(TESTS_PY)
%.py: 
	python nltk/test/$@

# Clean.  
#    - Erase any pyc and pyo files.
#    - Get rid of build/dist directories
clean:
	rm -rf build dist MANIFEST
	rm -f *.pyc nltk/*.pyc nltk/*/*.pyc
	rm -f *.pyo nltk/*.pyo nltk/*/*.pyo

# Distributions.
# Build all from scratch; and create links for convenient access.
distributions: clean sdist bdist
	(cd dist && ln -s nltk-*.noarch.rpm nltk.rpm)
	(cd dist && ln -s nltk-*.tar.gz nltk.tgz)
	(cd dist && ln -s nltk-*.zip nltk.zip)
	(cd dist && ln -s nltk-*.exe nltk.exe)

# Source distributions
sdist: gztardist zipdist

# Built distributions
bdist: rpmdist windist

# Produce dist/$(NAME)-$(VERSION).tar.gz
gztardist:
	python setup.py -q sdist --format=gztar

# Produce dist/$(NAME)-$(VERSION).tar.gz
zipdist:
	python setup.py -q sdist --format=zip

# Produce dist/$(NAME)-$(VERSION)-1.noarch.rpm
# Produce dist/$(NAME)-$(VERSION)-1.src.rpm
rpmdist:
	python setup.py -q bdist --format=rpm

# Produce dist/$(NAME)-$(VERSION).win32.exe
windist:
	python setup.py -q bdist --format=wininst
