# NLTK: Doctest Makefile
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

DOCTESTS = chunk.doctest corpus.doctest featgram.doctest featstruct.doctest logic.doctest misc.doctest parse.doctest sem.doctest stem.doctest tag.doctest tokenize.doctest toolbox.doctest toolbox_language.doctest tree.doctest treetransforms.doctest wordnet.doctest

ERRS := $(DOCTESTS:.doctest=.errs)
HTML := $(DOCTESTS:.doctest=.html)
PDF := $(DOCTESTS:.doctest=.pdf)

PAPER_SIZE = a4
RST = ../../doc/rst.py
RST2HTML = $(RST) --html --css ../../doc/nltkdoc.css
RST2LATEX = $(RST) --latex --$(PAPER_SIZE)
DOCTEST_FLAGS = --ellipsis --normalize_whitespace --udiff

# Use, e.g., "make USER=stevebird ..."
WEB = $(USER)@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs
BETA = $(WEB)/beta
RSYNC_OPTS = -arvz -e ssh --relative --cvs-exclude

.SUFFIXES: .errs .doctest
.PHONY: all

all: $(PDF) $(HTML)

errs: $(ERRS)
	ls -l $(ERRS)

.doctest.errs:
	python doctest_driver.py $(DOCTEST_FLAGS) $< > $@ 2>&1

%.html: %.doctest
	$(RST2HTML) $< 

%.tex: %.doctest
	$(RST2LATEX) $(REF) $< 

%.pdf: %.tex
	pdflatex $<
	rm -f $*.log $*.aux

rsync:
	rsync $(RSYNC_OPTS) . $(WEB)/doc/test/

clean:
	rm *.errs
