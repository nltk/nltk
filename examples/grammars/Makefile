# NLTK: Documentation Makefile
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

PUBLISH = ../../../nltk_data/packages/grammars

PACKAGE_DIRS = book_grammars sample_grammars #basque_grammars spanish_grammars
PACKAGES := $(addsuffix .zip, $(PACKAGE_DIRS))


ZIP = zip

all: publish

ci:
	svn ci -m "updated grammar files" 

zip: clean $(PACKAGES)

clean:	
	rm *.zip

%.zip: %
	$(ZIP) -r $< $<  -x \*.svn*

publish: zip
	cp $(PACKAGES) $(PUBLISH)
	svn commit -m "updated grammar files" ../../../nltk_data/packages/grammars
	$(MAKE) -C ../.. pkg_index