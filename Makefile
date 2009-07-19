# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#	 Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

PYTHON = python
VERSION = $(shell $(PYTHON) -c 'import nltk; print nltk.__version__' | sed '/^Warning: */d')
NLTK_URL = $(shell $(PYTHON) -c 'import nltk; print nltk.__url__' | sed '/^Warning: */d')
GOOGLE_ACCT = StevenBird1
UPLOAD = $(PYTHON) tools/googlecode_upload.py --project=nltk --config-dir=none --user=$(GOOGLE_ACCT) --labels=Featured

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
	$(UPLOAD) --summary="NLTK $(VERSION) RPM package" dist/nltk-$(VERSION)*.rpm
	$(UPLOAD) --summary="NLTK $(VERSION) Debian package" dist/nltk_$(VERSION)-1_all.deb
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

doctest:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_FLAGS) $(DOCTEST_FILES)

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

dist: zipdist gztardist rpmdist windist debdist eggdist dmgdist

gztardist: clean_code
	ln -sf setup-distutils.py setup.py
	$(PYTHON) setup.py -q sdist --format=gztar
zipdist: clean_code
	ln -sf setup-distutils.py setup.py
	$(PYTHON) setup.py -q sdist --format=zip
rpmdist: clean_code
	ln -sf setup-distutils.py setup.py
	$(PYTHON) setup.py -q bdist --format=rpm
windist: clean_code
	ln -sf setup-distutils.py setup.py
	$(PYTHON) setup.py -q bdist --format=wininst
debdist: clean_code
	alien --to-deb --bump=0 dist/nltk-$(VERSION)*noarch.rpm
	mv *.deb dist/
eggdist: clean_code
	ln -sf setup-eggs.py setup.py
	$(PYTHON) setup.py bdist --formats=egg

docdist:
	find doc -print | egrep -v '.svn|.DS_Store' | zip dist/nltk-doc-$(VERSION).zip -@

datadist:
	find nltk_data -print | egrep -v '.svn|.DS_Store' | zip -n .zip:.gz dist/nltk-data-$(VERSION).zip -@

nightlydist: codedist
	REVISION = `svn info | grep Revision: | sed "s/Revision: //"`

checksums:
	md5 dist/nltk-$(VERSION).tar.gz
	openssl sha1 dist/nltk-$(VERSION).tar.gz 
	openssl rmd160 dist/nltk-$(VERSION).tar.gz

pypi:
	ln -sf setup-eggs.py setup.py
	python setup-eggs.py register
	python setup-eggs.py sdist upload
	python setup-eggs.py bdist upload

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
	mkdir -p nltk-$(VERSION)
	$(PM) -d ./nltk.pmdoc -o nltk-$(VERSION)/$(NLTK_PKG)
	rm -f dist/$(NLTK_DMG)
	hdiutil create dist/$(NLTK_DMG) -srcfolder nltk-$(VERSION)

########################################################################
# DATA
########################################################################

data_index:
	echo "use make pkg_index"

pkg_index:
	$(PYTHON) tools/build_pkg_index.py ../nltk_data http://nltk.googlecode.com/svn/trunk/nltk_data/packages ../nltk_data/index.xml
	svn commit -m "updated data index" ../nltk_data/index.xml

########################################################################
# CLEAN
########################################################################

.PHONY: clean clean_up

clean:	clean_up
	rm -rf build iso dist MANIFEST $(MACROOT) nltk-$(VERSION)
	$(MAKE) -C doc clean
	$(MAKE) -C javasrc clean
#	rm -f nltk/nltk.jar

clean_up: clean_code
	$(MAKE) -C doc clean_up

clean_code:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	rm -f `find . -name '*~'`
	rm -f MANIFEST # regenerate manifest from MANIFEST.in
