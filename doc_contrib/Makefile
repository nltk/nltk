# NLTK: Doc Makefile
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

#WEB = $(USER)@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs

RST2HTML = ../doc/rst2html.py

STYLESHEET_PATH = ../doc

EPYDOC_OPTS = --name=nltk --navlink="nltk $(NLTK_VERSION)"\
              --url=$(NLTK_URL) --inheritance=listed
RSYNC_OPTS = -lrtvz -e ssh --relative --cvs-exclude

.SUFFIXES: .txt .html

.PHONY: sem

all: sem

clean:
	$(MAKE) -C sem clean

.txt.html:
	$(RST2HTML) --stylesheet-path=$(STYLESHEET_PATH) $< > $@

sem:
	$(MAKE) -C sem all

#rsync:
#	rsync $(RSYNC_OPTS) . $(WEB)/doc_contrib/

PUBLISH = ../../doc/contrib

publish:
	$(MAKE) -C sem publish
