# Natural Language Toolkit: Primary Makefile
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

DISTRIBUTIONS = distributions
NLTK_VERSION = 1.1a

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

all: documentation test distributions

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

distributions:
	rm -rf $(DISTRIBUTIONS)
	mkdir -p $(DISTRIBUTIONS)
	@echo "Building nltk distributions..."
	$(MAKE) -C src distributions
	cp src/dist/* $(DISTRIBUTIONS)
	@echo "Building nltk_corpora distributions..."
	rm -f nltk_corpora
	ln -s data nltk_corpora
	tar -cvzf $(DISTRIBUTIONS)/nltk_corpora-$(NLTK_VERSION).tgz \
	    nltk_corpora
	zip $(DISTRIBUTIONS)/nltk_corpora-$(NLTK_VERSION).zip \
	    nltk_corpora
	rm -f nltk_corpora
	@echo "Building nltk_contrib distributions..."
	$(MAKE) -C contrib distributions
	cp contrib/dist/* $(DISTRIBUTIONS)

clean:
	$(MAKE) -C doc clean
	$(MAKE) -C psets clean
	$(MAKE) -C src clean
	rm -rf $(DISTRIBUTIONS)
