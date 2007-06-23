# NLTK: Doctest Makefile
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

DOCTESTS = chunk.doctest corpus.doctest featgram.doctest featstruct.doctest logic.doctest misc.doctest parse.doctest sem.doctest stem.doctest tag.doctest tokenize.doctest toolbox.doctest toolbox_language.doctest tree.doctest treetransforms.doctest wordnet.doctest

ERRS := $(DOCTESTS:.doctest=.errs)

DOCTEST_FLAGS = --ellipsis --normalize_whitespace

.SUFFIXES: .errs .doctest
.PHONY: all

all: $(ERRS)
	ls -l $(ERRS)

.doctest.errs:
	python doctest_driver.py $(DOCTEST_FLAGS) $< > $@ 2>&1

clean:
	rm *.errs
