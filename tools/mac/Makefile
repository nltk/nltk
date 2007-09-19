# Natural Language Toolkit: OS X Distribution Makefile
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Joshua Ritterman <validus@gmail.com>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

PYTHON = python
#NLTK_VERSION = $(shell python -c 'import nltk; print nltk.__version__')
NLTK_VERSION = "0.9b2"
NLTK_ZIP = ../../dist/nltk-$(NLTK_VERSION).zip
PM = /Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker

.PHONY: pkg data-root lib-root clean

pkg: data-root lib-root
	$(PM) -build -proj ./Data_installer/nltk_data.pmproj \
		-p /tmp/nltk_data.pkg
	$(PM) -build -proj ./NLTKLibrary_installer/NLTKLibrary.pmproj \
		-p /tmp/NLTKLibrary.pkg
	$(PM) -build -proj ./NLTK.pmproj -p ../../dist/nltk-$(NLTK_VERSION).mpkg

clean:
	rm -rf ./Data_installer/root
	rm -rf ./NLTKLibrary_installer/root

data-root:
	rm -rf ./Data_installer/root
	mkdir -p ./Data_installer/root/usr/share/nltk/
	cp -R ../../data ./Data_installer/root/usr/share/nltk/
	chmod -R g+r ./Data_installer/root/usr/share/nltk

lib-root: $(NLTK_ZIP)
	rm -rf ./NLTKLibrary_installer/root
	mkdir -p ./NLTKLibrary_installer/root/tmp
	mkdir -p ./NLTKLibrary_installer/root/tmp/nltk-installer
	unzip $(NLTK_ZIP) -d ./NLTKLibrary_installer/root/tmp
	mv ./NLTKLibrary_installer/root/tmp/nltk-$(NLTK_VERSION)/ \
	   ./NLTKLibrary_installer/root/tmp/nltk-installer/

# This target should in theory have additional dependencies, to make
# sure it gets rebuilt when appropriate.
$(NLTK_ZIP):
	$(MAKE) -C ../.. zipdist
