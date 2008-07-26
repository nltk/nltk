# Natural Language Toolkit: OS X Distribution Makefile
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Joshua Ritterman <validus@gmail.com>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

PYTHON = python
DIST = ../../dist
NLTK_VERSION = nltk-$(shell python -c 'import nltk; print nltk.__version__')
NLTK_ZIP = $(DIST)/$(NLTK_VERSION).zip
NLTK_PKG = $(NLTK_VERSION)/$(NLTK_VERSION).pkg
NLTK_TIGER_DMG = $(NLTK_VERSION)-macosx10.4.dmg
NLTK_DMG = $(NLTK_VERSION).dmg
ROOT = ./MyRoot
LIB_PATH = $(ROOT)/tmp
LIB_PATH_VERSION = $(LIB_PATH)/$(NLTK_VERSION)
LIB_PATH_INST = $(LIB_PATH)/nltk-installer/
DATA_PATH = $(ROOT)/usr/share/nltk/
PM = /Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker 

.PHONY: clean

# this should work for both Leopard and Tiger, built under Leopard
$(NLTK_DMG): copy NLTK.pmdoc
	mkdir -p $(NLTK_VERSION)
	$(PM) -d ./nltk.pmdoc -o $(NLTK_PKG)
	rm -f $(NLTK_DMG)
	hdiutil create $(NLTK_DMG) -srcfolder $(NLTK_VERSION)
	cp $(NLTK_DMG) $(DIST)

# this works for Tiger, built under Tiger
$(NLTK_TIGER_DMG): copy NLTK.pmproj
	mkdir -p $(NLTK_VERSION)
	$(PM) -build -proj ./nltk.pmproj -p $(NLTK_PKG)
	rm -f $(NLTK_TIGER_DMG)
	hdiutil create $(NLTK_TIGER_DMG) -srcfolder $(NLTK_VERSION)
	cp $(NLTK_TIGER_DMG) $(DIST)

copy:
	rm -rf $(ROOT)
	mkdir -p $(DATA_PATH) $(LIB_PATH_INST)
	unzip $(NLTK_ZIP) -d $(LIB_PATH)
	mv $(LIB_PATH_VERSION)/* $(LIB_PATH_INST)
	rmdir $(LIB_PATH_VERSION)
	cp -R ../../data $(DATA_PATH)
	cp ../../LICENSE.txt ../../README.txt Resources/
	chmod -R g+r $(DATA_PATH)
	touch copy

clean:
	rm -rf ./nltk/root $(NLTK_VERSION) $(NLTK_DMG) copy
