# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#	 Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

PYTHON = python
VERSION = $(shell $(PYTHON) -c 'import nltk; print nltk.__version__' | sed '/^Warning: */d')
NLTK_URL = $(shell $(PYTHON) -c 'import nltk; print nltk.__url__' | sed '/^Warning: */d')
GOOGLE_ACCT = StevenBird1
UPLOAD = $(PYTHON) tools/googlecode_upload.py --project=nltk --config-dir=none --user=$(GOOGLE_ACCT) --labels=Featured

MACPORTS = http://trac.macports.org/browser/trunk/dports/python
PORT24 = $(MACPORTS)/py-nltk/Portfile?format=txt
PORT25 = $(MACPORTS)/py25-nltk/Portfile?format=txt
PORT26 = $(MACPORTS)/py26-nltk/Portfile?format=txt
LMACPORTS = ~/ports/python
LPORT24 = $(LMACPORTS)/py-nltk/Portfile
LPORT25 = $(LMACPORTS)/py25-nltk/Portfile
LPORT26 = $(LMACPORTS)/py26-nltk/Portfile

.PHONY: usage all doc clean clean_code clean_up

usage:
	@echo "make dist -- Build distributions (output to dist/)"
	@echo "make python -- Fetch Python distributions"
	@echo "make upload -- Upload files to NLTK website"
	@echo "make clean -- Remove all built files and temporary files"
	@echo "make clean_up -- Remove temporary files"

all: dist

upload:
	$(UPLOAD) --summary="NLTK $(VERSION) for Windows" dist/nltk-$(VERSION)*.win32.exe
	$(UPLOAD) --summary="NLTK $(VERSION) for Mac" dist/nltk-$(VERSION)*.dmg
	$(UPLOAD) --summary="NLTK $(VERSION) Source (zip)" dist/nltk-$(VERSION)*.zip
	$(UPLOAD) --summary="NLTK $(VERSION) Source (tgz)" dist/nltk-$(VERSION)*.tar.gz
# 	$(UPLOAD) --summary="NLTK $(VERSION) RPM package" dist/nltk-$(VERSION)*.noarch.rpm
#	$(UPLOAD) --summary="NLTK $(VERSION) Debian package" dist/nltk_$(VERSION)-1_all.deb
	$(UPLOAD) --summary="NLTK $(VERSION) Egg" dist/nltk-$(VERSION)*.egg
	$(UPLOAD) --summary="NLTK-Contrib $(VERSION)" ../nltk_contrib/dist/nltk_contrib-$(VERSION)*.zip

doc:
	$(MAKE) -C doc all

########################################################################
# TESTING
########################################################################

DOCTEST_DRIVER = nltk/test/doctest_driver.py
DOCTEST_FLAGS = --ellipsis --normalize_whitespace
DOCTEST_FILES = nltk/test/*.doctest
DOCTEST_CODE_FILES = nltk/*.py nltk/*/*.py

doctest:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_FLAGS) $(DOCTEST_FILES)

doctest_code:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_FLAGS) $(DOCTEST_CODE_FILES)

demotest:
	find nltk -name "*.py"\
        -and -not -path *misc* \
        -and -not -name brown_ic.py \
        -exec echo ==== '{}' ==== \; -exec python '{}' \;

########################################################################
# JAVA
########################################################################

jar: nltk/nltk.jar

JAVA_SRC = $(shell find javasrc/org/nltk -name '*.java')
nltk/nltk.jar: $(JAVA_SRC)
	$(MAKE) -C javasrc jar
	cp javasrc/nltk.jar nltk/nltk.jar

########################################################################
# DISTRIBUTIONS
########################################################################

dist: zipdist gztardist rpmdist windist eggdist dmgdist

gztardist: clean_code
	$(PYTHON) setup.py -q sdist --format=gztar
zipdist: clean_code
	$(PYTHON) setup.py -q sdist --format=zip
rpmdist: clean_code
	$(PYTHON) setup.py -q bdist --format=rpm
windist: clean_code
	$(PYTHON) setup.py -q bdist --format=wininst
	rm dist/nltk-$(VERSION).win32.exe || true
	mv dist/nltk-$(VERSION)*.exe dist/nltk-$(VERSION).win32.exe
#debdist: clean_code
#	alien --to-deb --bump=0 dist/nltk-$(VERSION)*noarch.rpm
#	mv *.deb dist/
eggdist: clean_code
	$(PYTHON) setup.py bdist --formats=egg

docdist:
	find doc -print | egrep -v '.svn|.DS_Store' | zip dist/nltk-doc-$(VERSION).zip -@

datadist:
	find nltk_data -print | egrep -v '.svn|.DS_Store' | zip -n .zip:.gz dist/nltk-data-$(VERSION).zip -@

nightlydist: codedist
	REVISION = `svn info | grep Revision: | sed "s/Revision: //"`

checksums.txt: dist/nltk-$(VERSION).tar.gz
	echo Assuming dist/nltk-$(VERSION).tar.gz is identical to latest
	echo release at: http://code.google.com/p/nltk/downloads/list
	md5 dist/nltk-$(VERSION).tar.gz |\
	sed 's/MD5.*=/checksums           md5/' | sed 's/$$/ \\/' > checksums.txt
	openssl sha1 dist/nltk-$(VERSION).tar.gz |\
	sed 's/SHA1.*=/                    sha1/' | sed 's/$$/ \\/' >> checksums.txt
	openssl rmd160 dist/nltk-$(VERSION).tar.gz |\
	sed 's/RIPEMD160.*=/                    rmd160/' >> checksums.txt

pypi:
	$(PYTHON) setup.py register
	$(PYTHON) setup.py sdist upload
	$(PYTHON) setup.py bdist upload

macports: checksums.txt
	rm -rf ~/ports/python/py*-nltk
	mkdir -p ~/ports/python/py-nltk ~/ports/python/py25-nltk ~/ports/python/py26-nltk
	wget $(PORT24) -O $(LPORT24)
	wget $(PORT25) -O $(LPORT25)
	wget $(PORT26) -O $(LPORT26)
	cp $(LPORT24) $(LPORT24).orig
	cp $(LPORT25) $(LPORT25).orig
	cp $(LPORT26) $(LPORT26).orig
	$(PYTHON) tools/update_checksums.py $(LPORT24) checksums.txt $(VERSION)
	$(PYTHON) tools/update_checksums.py $(LPORT25) checksums.txt $(VERSION)
	$(PYTHON) tools/update_checksums.py $(LPORT26) checksums.txt $(VERSION)
	diff -u $(LPORT24).orig $(LPORT24) > dist/Portfile-py-nltk.diff
	diff -u $(LPORT25).orig $(LPORT25) > dist/Portfile-py25-nltk.diff
	diff -u $(LPORT26).orig $(LPORT26) > dist/Portfile-py26-nltk.diff
	echo now run "portindex", test install the ports, and submit

########################################################################
# OS X
########################################################################

NLTK_ZIP = dist/nltk-$(VERSION).zip
NLTK_PKG = nltk-$(VERSION).pkg
NLTK_DMG = nltk-$(VERSION).dmg
MACROOT = ./MacRoot
LIB_PATH = $(MACROOT)/tmp/nltk-installer/
PM = /Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker 

# this should work for both Leopard and Tiger, built under Leopard
dmgdist:
	rm -rf $(MACROOT)
	mkdir -p $(LIB_PATH)
	unzip $(NLTK_ZIP) -d $(LIB_PATH)
	mv $(LIB_PATH)/nltk-$(VERSION)/* $(LIB_PATH)
	rmdir $(LIB_PATH)/nltk-$(VERSION)
	chmod -R a+r $(MACROOT)
ifeq ($(shell uname), Darwin)
	mkdir -p nltk-$(VERSION)
	$(PM) -d ./NLTK.pmdoc -o nltk-$(VERSION)/$(NLTK_PKG)
	rm -f dist/$(NLTK_DMG)
	hdiutil create dist/$(NLTK_DMG) -srcfolder nltk-$(VERSION)
endif

########################################################################
# API DOCUMENTATION
########################################################################

api:
	echo install NLTK first
	sphinx-apidoc -F -H NLTK -o api nltk
	$(MAKE) -C api html
	rm ../api/*
	mv api/_build/html/* ../api

########################################################################
# DATA
########################################################################

pkg_index:
	$(PYTHON) tools/build_pkg_index.py ../nltk_data http://nltk.googlecode.com/svn/trunk/nltk_data/packages ../nltk_data/index.xml
	svn commit -m "updated data index" ../nltk_data/index.xml

########################################################################
# CLEAN
########################################################################

.PHONY: clean clean_up

clean:	clean_up
	rm -rf build iso dist api MANIFEST $(MACROOT) nltk-$(VERSION)
	$(MAKE) -C javasrc clean
#	rm -f nltk/nltk.jar

clean_up: clean_code
	$(MAKE) -C doc clean_up

clean_code:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	rm -f `find . -name '*~'`
	rm -f MANIFEST # regenerate manifest from MANIFEST.in
