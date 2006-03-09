# NLTK-LITE: Presentation Slides Makefile
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

WEB = stevenbird@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs/lite
TEX = introduction.tex programming.tex tag.tex field.tex
PDF = introduction.pdf programming.pdf tag.pdf field.pdf

CSS_STYLESHEET_PATH = ../default.css
RST2HTML = rst2html.py

.SUFFIXES: .txt .html .tex .pdf

.PHONY: all clean rsync

all: $(PDF) index.html

clean:
	rm -f $(PDF) *.log *.aux *.snm *.vrb index*.html

index.html:	index.txt
	$(RST2HTML) --stylesheet-path=$(CSS_STYLESHEET_PATH) index.txt > index.html

.tex.pdf:
	pdflatex $<
	rm $@
	pdflatex $<

rsync:
	rsync -arz -e ssh index.txt index.html $(TEX) $(PDF) $(WEB)/doc/slides/


