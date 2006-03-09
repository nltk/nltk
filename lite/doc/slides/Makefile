# NLTK-LITE: Presentation Slides Makefile
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

TEX = introduction.tex tag.tex field.tex
PDF = introduction.pdf tag.pdf field.pdf

CSS_STYLESHEET_PATH = ../default.css
RST2HTML = rst2html.py

.SUFFIXES: .txt .html .tex .pdf

all: $(PDF)

clean:
	rm -f $(PDF) $(HTML) *.tex *.log *.aux

index.html:	index.txt
	$(RST2HTML) --stylesheet-path=$(CSS_STYLESHEET_PATH) index.txt > index.html

.tex.pdf:
	pdflatex $<
