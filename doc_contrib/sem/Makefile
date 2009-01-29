# Contrib Docs Makefile
# Adapted from Docs Makefile
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

PAPER_SIZE = a4

DOCS =  gluesem.txt drt.txt prover.txt hole.txt

#REF_EXTENSION = .ref

PDF := $(DOCS:.txt=.pdf)
HTML := $(DOCS:.txt=.html)
ERRS := $(DOCS:.txt=.errs)
#REF := $(DOCS:.txt=$(REF_EXTENSION))
PY := $(DOCS:.txt=.py)
TEX := $(DOCS:.txt=.tex)

BIBTEX_FILE = refs.bib

PYTHON = python
PDFLATEX = TEXINPUTS=".:../../doc:" pdflatex -halt-on-error
EXAMPLES = ../../doc/examples.py
RST = ../../doc/rst.py
#RST2REF = $(RST) --ref
RST2HTML = $(RST) --html
RST2LATEX = $(RST) --latex --$(PAPER_SIZE) --latex_stylesheet_path=$(LATEX_STYLESHEET_PATH) --bibtex_file=$(BIBTEX_FILE)
DOCTEST = PYTHONPATH=../.. $(PYTHON) ../../nltk/test/doctest_driver.py
BIBTEX = bibtex -terse

# <http://www.spinellis.gr/sw/textproc/bib2xhtml/>
# BIB2XHTML = bib2xhtml -s named

# WEB = $(USER)@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs
# BETA = $(WEB)/beta
# RSYNC_OPTS = -arvz -e ssh --relative --cvs-exclude

LATEX_STYLESHEET_PATH = ../../doc/definitions.sty

.SUFFIXES: .txt .html .pdf .errs .py

help: usage
usage:
	@echo "Usage:"
	@echo "    make all         -- Build HTML & PDF output"
	@echo "    make html        -- Build HTML output"
	@echo "    make pdf         -- Build PDF output"
	@echo "    make errs        -- Run doctest to generate .errs files"
	@echo "    make clean       -- Remove all built files"

all: html pdf examples clean_up
html: $(HTML) 
pdf: $(PDF)
examples: $(PY)
errs: $(ERRS)
	ls -l $(ERRS)

clean:	clean_up
	rm -f $(PDF) $(HTML) $(ERRS) $(REF) $(PY) $(TEX)
	rm -rf tree_images

clean_up:
	rm -f *.log *.aux *.out *.errs *~ *.bbl *.idx *.ilg *.ind *.toc *.blg

# .PRECIOUS: $(REF)

# %$(REF_EXTENSION): %.txt revision.txt
# 	$(RST2REF) $<

%.html: %.txt revision.txt
	$(RST2HTML) $< 

%.tex: %.txt revision.txt
	$(RST2LATEX) $< 

revision.txt: $(DOCS)
	echo "This document is" > revision.txt
	svn info | grep Revision >> revision.txt
	date >> revision.txt


# This fairly complex target here will cause pdflatex to only generate
# output if it fails; and to clean up after itself if it fails.  Also,
# it will only run a second pass if it detects that it's necessary (by
# scanning the log file for a warning message).
%.pdf: %.tex
	rm -f $*.ind
	@echo "pdflatex $< -> $*.pdf (first pass)"
	@(true | $(PDFLATEX) $< >/dev/null) || \
                 (cat $*.log && rm -f $*.pdf && false)
	@if [ "`grep -i 'Warning.*Rerun' $*.log`" ]; \
	    then \
	        echo "pdflatex $< -> $*.pdf (second pass)";\
	        (true | $(PDFLATEX) $< >/dev/null) || \
                       (cat $*.log && rm -f $*.pdf && false);\
	    fi
	@(if [ -e $*.idx ]; \
	    then \
	        echo "makeindex $*.idx"; makeindex $*.idx; \
	    fi)
	@echo "pdflatex $< -> $*.pdf (last pass)"
	@(true | $(PDFLATEX) $< >/dev/null) || \
                 (cat $*.log && rm -f $*.pdf && false)
	@echo "cleaning up latex temp files..."
	rm -f $*.log $*.aux $*.out $*.errs $*.bbl 
	rm -f $*.idx $*.ilg $*.ind $*.toc $*.blg


.txt.errs:
	$(DOCTEST) $< --ellipsis --normalize_whitespace --udiff &> $@

rsync-en:
	rsync $(RSYNC_OPTS) . $(WEB)/doc/en/

rsync-en-beta:
	rsync $(RSYNC_OPTS) . $(BETA)/doc/en/

.txt.py:
	$(PYTHON) $(EXAMPLES) $< > $@

PUBLISH = ../../../doc/contrib/sem

publish:
	cp *.{pdf,html} $(PUBLISH)
	cp images/*.png $(PUBLISH)/images
	svn add $(PUBLISH)/* $(PUBLISH)/images/*
	python ../../tools/svnmime.py $(PUBLISH)/* $(PUBLISH)/images/*
