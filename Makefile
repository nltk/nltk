# Natural Language Toolkit: Primary Makefile
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

all: documentation test distributions

usage: help
help:
	# Usage:
	#     make [all | documentation | distributions | test | clean | help]

documentation:
	$(MAKE) -C doc
	$(MAKE) -C psets

test:
	$(MAKE) -C src test

distributions:
	$(MAKE) -C src distributions

clean:
	$(MAKE) -C doc clean
	$(MAKE) -C psets clean
	$(MAKE) -C src clean
