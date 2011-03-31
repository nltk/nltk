# NLTK: Documentation Makefile
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

PUBLISH = ../../doc

PYTHON = python

NLTK_VERSION = $(shell $(PYTHON) -c 'import nltk; print nltk.__version__')
NLTK_URL = $(shell $(PYTHON) -c 'import nltk; print nltk.__url__')

RST2HTML = rst2html.py

STYLESHEET_PATH = .

EPYDOC_OPTS = --name=nltk --navlink="nltk $(NLTK_VERSION)"\
              --url=$(NLTK_URL) --inheritance=listed --debug
RSYNC_OPTS = -lrtvz -e ssh --relative --cvs-exclude --omit-dir-times

.SUFFIXES: .txt .html

.PHONY: book pt-br slides api rsync .api.done howto rsync-api

all: book slides api howto

clean:	clean_up
	rm -rf api
	$(MAKE) -C book clean
	$(MAKE) -C howto clean
	$(MAKE) -C slides clean

clean_up:
	TEXFILES=`find . -maxdepth 1 -name '*.tex' \
			 -and -not -name 'xelatexsymbols.tex'`; \
	    rm -f *.log *.aux $$TEXFILES *.out *.errs *~
	$(MAKE) -C book clean_up
	$(MAKE) -C howto clean_up
	$(MAKE) -C slides clean_up

.txt.html:
	$(RST2HTML) --stylesheet-path=$(STYLESHEET_PATH) $< > $@

book:
	$(MAKE) -C book all

slides:
	$(MAKE) -C slides

howto:
	$(MAKE) -C howto

api:	.api.done
	epydoc $(EPYDOC_OPTS) -o api ../nltk
	touch .api.done

publish: publish-book publish-howto publish-api
	svn commit $(PUBLISH)

publish-book:
	$(MAKE) -C book publish
	cp default.css $(PUBLISH)
	cp images/*.png $(PUBLISH)/images/
	svn add $(PUBLISH)/default.css $(PUBLISH)/images/*
	$(PYTHON) ../tools/svnmime.py $(PUBLISH)/default.css $(PUBLISH)/images/*

publish-howto:
	$(MAKE) -C howto publish

publish-api:
	cp api/* $(PUBLISH)/api
	svn add $(PUBLISH)/api/*
	$(PYTHON) ../tools/svnmime.py $(PUBLISH)/api/*
