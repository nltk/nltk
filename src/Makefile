# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# Epydoc executable
EPYDOC = epydoc

# Get the version of nltk
NLTK_VERSION=$(shell python -c 'import nltk; print nltk.__version__')

all: distributions

usage:
	@echo "make distributions -- Build distributions (output to dist/)"
	@echo "make test -- Run unit tests"
	@echo "make checkdocs -- Check docstrings for completeness"
	@echo "make clean -- Remove temporary and built files"

# Tests.
test: 
	python nltk/test/__init__.py -v -c coverage

# Clean.  
#    - Erase any pyc and pyo files.
#    - Get rid of build/dist directories
#    - Erase the MANIFEST file (it's generated from MANIFEST.in)
clean:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	rm -rf build dist MANIFEST

# Distributions. Build all from scratch.
distributions: clean sdist bdist

# Source distributions
sdist: gztardist zipdist

# Built distributions
bdist: rpmdist windist

# Produce dist/$(NAME)-$(VERSION).tar.gz
gztardist: INSTALL.TXT
	python setup.py -q sdist --format=gztar

# Produce dist/$(NAME)-$(VERSION).tar.gz
zipdist: INSTALL.TXT
	python setup.py -q sdist --format=zip

# Produce dist/$(NAME)-$(VERSION)-1.noarch.rpm
# Produce dist/$(NAME)-$(VERSION)-1.src.rpm
rpmdist: INSTALL.TXT
	python setup.py -q bdist --format=rpm

# Produce dist/$(NAME)-$(VERSION).win32.exe
windist: INSTALL.TXT
	python setup.py -q bdist --format=wininst

checkdocs:
	$(EPYDOC) -v --check nltk

# Automatically add the appropriate version number.
INSTALL.TXT: INSTALL.TXT.in
	cat $< | sed "s/??\.??/$(NLTK_VERSION)/g" >$@
