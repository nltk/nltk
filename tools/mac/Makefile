# Natural Language Toolkit: OS X Distribution Makefile
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Joshua Ritterman <validus@gmail.com>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

PYTHON = python
NLTK_VERSION = $(shell python -c 'import nltk; print nltk.__version__')
NLTK_ZIP = ../../dist/nltk-$(NLTK_VERSION).zip
PM = /Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker

.PHONY: pkg corpus-root lib-root clean

pkg: corpus-root lib-root
	$(PM) -build -proj ./Corpus_installer/nltk_corpora.pmproj \
		-p ./pkgs/nltk_corpora.pkg
	$(PM) -build -proj ./NLTKLibrary_installer/NLTKLibrary.pmproj \
		-p ./pkgs/NLTKLibrary.pkg
	$(PM) -build -proj ./NLTK.pmproj -p ../../dist/nltk-$(NLTK_VERSION).mpkg

clean:
	rm -rf ./Corpus_installer/root
	rm -rf ./NLTKLibrary_installer/root

corpus-root:
	rm -rf ./Corpus_installer/root
	mkdir -p ./Corpus_installer/root/usr/share/nltk/
	cp -R ../../data/corpora ./Corpus_installer/root/usr/share/nltk/
	chmod -R g+r ./Corpus_installer/root/usr/share/nltk

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
