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
LIB_TMP = ./nltk_library/root/tmp
DATA_PATH = ./nltk_data/root/usr/share/nltk/
PM = /Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker -build -proj

.PHONY: clean

$(NLTK_DMG): /tmp/nltk_data.pkg /tmp/nltk_library.pkg
	mkdir -p $(NLTK_VERSION)
	$(PM) ./nltk.pmproj -p $(NLTK_MPKG)
	rm -f $(NLTK_DMG)
	hdiutil create $(NLTK_DMG) -srcfolder $(NLTK_VERSION)
	cp $(NLTK_DMG) $(DIST)

clean:
	rm -rf ./nltk_data/root ./nltk_library/root
	rm -rf $(NLTK_VERSION)
	rm -f $(NLTK_DMG)

nltk_data.pkg:
	rm -rf ./nltk_data/root
	mkdir -p $(DATA_PATH)
	cp -R ../../data $(DATA_PATH)
	chmod -R g+r $(DATA_PATH)
	$(PM) ./nltk_data/nltk_data.pmproj -p /tmp/nltk_data.pkg

/tmp/nltk_library.pkg: $(NLTK_ZIP)
	rm -rf ./nltk_library_installer/root
	mkdir -p $(LIB_TMP)/nltk-installer
	unzip $(NLTK_ZIP) -d $(LIB_TMP)
	mv $(LIB_TMP)/$(NLTK_VERSION)/* \
	   $(LIB_TMP)p/nltk-installer/
	rmdir $(LIB_TMP)/$(NLTK_VERSION)
	$(PM) ./nltk_library_installer/nltk_library.pmproj -p /tmp/nltk_library.pkg

# This target should in theory have additional dependencies, to make
# sure it gets rebuilt when appropriate.
$(NLTK_ZIP):
	$(MAKE) -C ../.. zipdist

