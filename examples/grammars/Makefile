# NLTK: Documentation Makefile
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

DATADIR =  ../../../nltk_data
PUBLISH = $(DATADIR)/packages/grammars

PACKAGE_DIRS = book_grammars sample_grammars #basque_grammars spanish_grammars
PACKAGES := $(addsuffix .zip, $(PACKAGE_DIRS))

ZIP = zip

define remove
  $(if $(wildcard $1), rm $1,)
endef

all: publish

ci:
	git ci -m "updated grammar files" 

zip: clean $(PACKAGES)


clean:	
	$(call remove, *.zip)

%.zip: %
	$(ZIP) -r $< $<
#	git add *zip

publish: zip
	cp $(PACKAGES) $(PUBLISH)
	$(MAKE) -C $(DATADIR) grammars
	$(MAKE) -C $(DATADIR) pkg_index
