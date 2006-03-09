# NLTK-LITE: Tutorial Makefile
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

WEB = stevenbird@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs/lite

RST2HTML = rst2html.py

STYLESHEET_PATH = .

EPYDOC_OPTS = -n nltk-lite --navlink "nltk-lite $(NLTK_VERSION)"\
              -u $(NLTK_URL) --inheritance=listed
RSYNC_OPTS = -arvvz -e ssh --relative --cvs-exclude

.SUFFIXES: .txt .html

.PHONY: en pt-br slides api rsync

all: html en pt-br slides api
html: index.html

clean:
	rm -rf index.html api
	$(MAKE) -C en clean
	$(MAKE) -C pt-br clean
	$(MAKE) -C slides clean

.txt.html:
	$(RST2HTML) --stylesheet-path=$(STYLESHEET_PATH) $< > $@

en:
	$(MAKE) -C en all

pt-br:
	$(MAKE) -C pt-br all

slides:
	$(MAKE) -C slides

api:
	rm -rf api/*
	epydoc $(EPYDOC_OPTS) -o api ../nltk_lite

rsync:
	rsync $(RSYNC_OPTS) . $(WEB)/doc/
