# Natural Language Toolkit: Primary Makefile
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

DISTRIBUTIONS = distributions

# What's the version of the corpora?
CORPORA_VERSION = 0.3

# Get the current version of NLTK
NLTK_VERSION=$(shell export PYTHONPATH=src; \
	       python -c 'import nltk; print nltk.__version__')

.PHONY: all usage help doc documentation webpage test
.PHONY: distributions clean

usage: help
help:
	@echo "Usage:"
	@echo "    make all            -- Build documentation and"\
	                                 "distributions;"
	@echo "                           and run test cases"
	@echo "    make clean          -- Remove all built files"
	@echo
	@echo "    make documentation  -- Build all documentation"
	@echo
	@echo "    make distributions  -- Build source and binary"\
	                                 "distributions"
	@echo "                           (output to distributions/)"
	@echo "    make test           -- Run test cases"
	@echo
	@echo "    make webpage        -- Build the web page"
	@echo "                           (output to doc/built_webpage/)"
	@echo "    make xfer           -- Build and upload the web page"
	@echo
	@echo "    make webpage.tar.gz -- Build documentation archive"
	@echo "                           (output to doc/webpage.tar.gz)"
	@echo

# (distributions builds webpage)
all: test distributions

doc: documentation
docs: documentation
documentation:
	$(MAKE) -C doc
	$(MAKE) -C psets

webpage.tgz:
webpage.tar.gz:
	$(MAKE) -C doc webpage.tar.gz

web: webpage
html: webpage
webpage:
	$(MAKE) -C doc webpage

xfer:
	$(MAKE) -C doc xfer

test:
	$(MAKE) -C src test

distributions: distributions.init distributions.nltk distributions.corpora \
	       distributions.contrib distributions.webpage

distributions.init:
	rm -rf $(DISTRIBUTIONS)
	mkdir -p $(DISTRIBUTIONS)

distributions.nltk:
	@echo "Building nltk distributions..."
	$(MAKE) -C src distributions
	cp src/dist/* $(DISTRIBUTIONS)

NLTK_DATA = nltk-data-$(CORPORA_VERSION)
distributions.corpora:
	@echo "Building nltk_corpora distributions..."
	rm -f $(NLTK_DATA)
	ln -s data $(NLTK_DATA)
	tar -cvzhf $(DISTRIBUTIONS)/nltk-data-$(CORPORA_VERSION).tgz \
	    $(NLTK_DATA)/*.readme $(NLTK_DATA)/*.zip
	zip -rq $(DISTRIBUTIONS)/nltk-data-$(CORPORA_VERSION).zip $(NLTK_DATA)
	rm -f $(NLTK_DATA)

distributions.contrib:
	@echo "Building nltk_contrib distributions..."
	$(MAKE) -C contrib distributions
	cp contrib/dist/* $(DISTRIBUTIONS)

NLTK_DOCS = nltk-docs-$(NLTK_VERSION)
distributions.webpage:
	@echo "Packaging nltk webpage..."
	$(MAKE) -C doc webpage
	rm -f $(NLTK_DOCS)
	ln -s doc/built_webpage $(NLTK_DOCS)
	tar -czhf $(DISTRIBUTIONS)/nltk-$(NLTK_VERSION)-docs.tgz $(NLTK_DOCS)
	zip -rq $(DISTRIBUTIONS)/nltk-$(NLTK_VERSION)-docs.zip $(NLTK_DOCS)
	rm -f $(NLTK_DOCS)

clean:
	$(MAKE) -C doc clean
	$(MAKE) -C psets clean
	$(MAKE) -C src clean
	$(MAKE) -C contrib clean
	rm -rf $(DISTRIBUTIONS)
