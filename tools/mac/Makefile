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
PM = /Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker -build -proj

.PHONY: clean

$(NLTK_DMG):	nltk_data.pkg NLTKLibrary.pkg
	mkdir -p $(NLTK_VERSION)
	$(PM) ./NLTK.pmproj -p $(NLTK_MPKG)
	rm -f $(NLTK_DMG)
	hdiutil create $(NLTK_DMG) -srcfolder $(NLTK_VERSION)
	cp $(NLTK_DMG) $(DIST)

clean:
	rm -rf ./Data_installer/root
	rm -rf ./NLTKLibrary_installer/root
	rm -rf $(NLTK_VERSION) NLTKLibrary.pkg nltk_data.pkg
	rm -f $(NLTK_DMG)

nltk_data.pkg:
	rm -rf ./Data_installer/root
	mkdir -p ./Data_installer/root/usr/share/nltk/
	cp -R ../../data ./Data_installer/root/usr/share/nltk/
	chmod -R g+r ./Data_installer/root/usr/share/nltk
	$(PM) ./Data_installer/nltk_data.pmproj -p nltk_data.pkg

NLTKLibrary.pkg: $(NLTK_ZIP)
	rm -rf ./NLTKLibrary_installer/root
	mkdir -p ./NLTKLibrary_installer/root/tmp/nltk-installer
	unzip $(NLTK_ZIP) -d ./NLTKLibrary_installer/root/tmp
	mv ./NLTKLibrary_installer/root/tmp/$(NLTK_VERSION)/* \
	   ./NLTKLibrary_installer/root/tmp/nltk-installer/
	rmdir ./NLTKLibrary_installer/root/tmp/$(NLTK_VERSION)
	$(PM) ./NLTKLibrary_installer/NLTKLibrary.pmproj -p NLTKLibrary.pkg

# This target should in theory have additional dependencies, to make
# sure it gets rebuilt when appropriate.
$(NLTK_ZIP):
	$(MAKE) -C ../.. zipdist

