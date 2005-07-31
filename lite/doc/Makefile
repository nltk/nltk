# NLTK-LITE: Tutorial Makefile
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

TUTORIALS = index.txt
HTML =      index.html

RST2HTML = rst2html.py

STYLESHEET_PATH = .

.SUFFIXES: .txt .html

all: $(HTML)
html: $(HTML)

clean:
	rm -f $(PDF) $(HTML) *.tex *.log *.aux

.txt.html:
	$(RST2HTML) --stylesheet-path=$(STYLESHEET_PATH) $< > $@
