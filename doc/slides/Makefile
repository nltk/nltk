# Presentation Slides Makefile
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

WEB = $(USER)@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs

TEX = preface.tex introduction.tex programming.tex tag.tex chunk.tex data.tex
PDF := $(TEX:.tex=.pdf)

RST2HTML = ../rst.py --html

RSYNC_OPTS = -lrtvz -e ssh --relative --cvs-exclude

.SUFFIXES: .rst .html .tex .pdf

.PHONY: all clean

all: $(PDF) index.html

clean:	clean_up
	rm -f $(PDF) index.html

clean_up:
	rm -f *.log *.aux *.snm *.vrb *.out *.nav *.toc index*.html

index.html:	index.rst
	$(RST2HTML) index.rst > index.html

.tex.pdf:
	pdflatex $<
	pdflatex $<
	mkdir -p handouts
	sed 's/documentclass/documentclass[handout]/' < $< > handouts/$<
	pdflatex -output-directory handouts handouts/$<
	pdflatex -output-directory handouts handouts/$<

rsync:
	rsync $(RSYNC_OPTS) . $(WEB)/doc/slides/
