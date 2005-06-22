# NLTK-LITE: Tutorial Makefile
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

TUTORIALS = index.txt  preface.txt  introduction.txt  programming.txt  tokenize.txt  tag.txt  parse.txt
HTML =      index.html preface.html introduction.html programming.html tokenize.html tag.html parse.html
PDF =       index.pdf  preface.pdf  introduction.pdf  programming.pdf  tokenize.pdf  tag.pdf  parse.pdf

PYTHON = python
RST2HTML = rst2html.py
RST2LATEX = rst2latex.py

STYLESHEET_PATH = ..

.SUFFIXES: .txt .html .pdf

help: usage
usage:
	@echo "Usage:"
	@echo "    make all         -- Build HTML & PDF output"
	@echo "    make html        -- Build HTML output"
	@echo "    make pdf         -- Build PDF output"
	@echo "    make clean       -- Remove all built files"

all: $(HTML) $(PDF)
html: $(HTML)
pdf: $(PDF)
clean:
	rm -f $(PDF)

.txt.html:
	$(RST2HTML) --stylesheet-path=$(STYLESHEET_PATH) $< > $@

.txt.tex:
	$(RST2LATEX) $< > $@

.tex.pdf:
	$(PDFLATEX) $<

