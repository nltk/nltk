# Natural Language Toolkit: Primary Makefile
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

.PHONY: all usage help doc documentation webpage test
.PHONY: distributions clean

usage: help
help:
	@echo "Usage:"
	@echo "    make all            -- Build documentation and"\
                                          "distributions; and run test cases"
	@echo "    make clean          -- Remove all built files"
	@echo "    make documentation  -- Build all documentation"
	@echo "    make distributions  -- Build source and binary"\
	                                 "distributions"
	@echo "    make test           -- Run test cases"
	@echo "    make webpage        -- Build the web page"
	@echo "    make xfer           -- Build and upload the web page"
	@echo "    make webpage.tar.gz -- Build documentation archive"
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
	$(MAKE) -C src distributions

clean:
	$(MAKE) -C doc clean
	$(MAKE) -C psets clean
	$(MAKE) -C src clean
