# Natural Language Toolkit: OS X Distribution Makefile
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Joshua Ritterman <validus@gmail.com>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

PYTHON = python
DIST = ../../dist
NLTK_VERSION = nltk-$(shell python -c 'import nltk; print nltk.__version__')
NLTK_ZIP = $(DIST)/$(NLTK_VERSION).zip
NLTK_MPKG = $(NLTK_VERSION)/$(NLTK_VERSION).mpkg
NLTK_DMG = $(NLTK_VERSION).dmg
LIB_PATH = ./nltk/root/tmp
LIB_PATH_VERSION = $(LIB_PATH)/$(NLTK_VERSION)
LIB_PATH_INST = $(LIB_PATH)/nltk-installer/
DATA_PATH = ./nltk/root/usr/share/nltk/
PM = /Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker -build -proj

.PHONY: clean

$(NLTK_DMG): copy nltk.pmproj
	mkdir -p $(NLTK_VERSION)
	$(PM) ./nltk.pmproj -p $(NLTK_MPKG)
	rm -f $(NLTK_DMG)
	hdiutil create $(NLTK_DMG) -srcfolder $(NLTK_VERSION)
	cp $(NLTK_DMG) $(DIST)

copy:
	rm -rf ./nltk/root
	mkdir -p $(DATA_PATH) $(LIB_PATH_INST)
	unzip $(NLTK_ZIP) -d $(LIB_PATH)
	mv $(LIB_PATH_VERSION)/* $(LIB_PATH_INST)
	rmdir $(LIB_PATH_VERSION)
#	cp -R ../../data $(DATA_PATH)
	cp ../../LICENSE.txt ../../README.txt Resources/
	chmod -R g+r $(DATA_PATH)
	touch copy

clean:
	rm -rf ./nltk/root $(NLTK_VERSION) $(NLTK_DMG) copy
