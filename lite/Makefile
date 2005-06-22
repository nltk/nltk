# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Epydoc executable
EPYDOC = epydoc

# Python executable
PYTHON = python

# Get the version of nltk
NLTK_VERSION=$(shell python -c 'import nltk_lite; print nltk_lite.__version__')

# CVS snapshot build directory
DATE = $(shell date +%F)
CVS_SNAPSHOT = nltk_lite_$(DATE)

all: distributions

usage:
	@echo "make distributions -- Build distributions (output to dist/)"
	@echo "make test -- Run unit tests"
	@echo "make checkdocs -- Check docstrings for completeness"
	@echo "make clean -- Remove temporary and built files"

# Tests.
test: 
	$(PYTHON) runtests.py -v -c coverage

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

checkapidocs:
	$(EPYDOC) -v --check nltk_lite

apidocs:
	$(EPYDOC) -o doc/api nltk_lite

tutorials:
	tar czvf tutorials.tgz --exclude=CVS --exclude==api doc

corpora:
	tar czvf corpora.tgz --exclude=CVS corpora

# Automatically add the appropriate version number.
INSTALL.TXT: INSTALL.TXT.in
	cat $< | sed "s/??\.??/$(NLTK_VERSION)/g" >$@

# CVS snapshot
tgz:
	echo "build apidocs and tutorials manually"
	rm -rf $(CVS_SNAPSHOT)
	cvs -d:ext:stevenbird@cvs.sourceforge.net:/cvsroot/nltk co nltk/lite
	mv nltk $(CVS_SNAPSHOT)
#	cp -r doc/api $(CVS_SNAPSHOT)/lite/doc/api
	cp doc/en/*.html $(CVS_SNAPSHOT)/lite/doc/en
	tar cvzf $(CVS_SNAPSHOT).tgz $(CVS_SNAPSHOT)
