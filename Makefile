# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#	 Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

PYTHON = python
NLTK_VERSION = $(shell python -c 'import nltk_lite; print nltk_lite.__version__')

.PHONY: usage all doc clean clean_code clean_up

usage:
	@echo "make dist -- Build distributions (output to dist/)"
	@echo "make python -- Fetch Python distributions"
	@echo "make rsync -- Upload files to NLTK website"
	@echo "make clean -- Remove all built files and temporary files"
	@echo "make clean_up -- Remove temporary files"

all: dist

doc:
	$(MAKE) -C doc all

########################################################################
# TESTING
########################################################################

DOCTEST_DRIVER = nltk_lite/test/doctest_driver.py
DOCTEST_FLAGS = --ellipsis --normalize_whitespace
DOCTEST_FILES = nltk_lite/test/*.doctest

doctest:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_FLAGS) $(DOCTEST_FILES)

########################################################################
# DISTRIBUTIONS
########################################################################

.PHONY: dist codedist docdist corporadist exampledist .dist.done

dist: codedist docdist exampledist corporadist
	touch .dist.done

codedist: clean_code INSTALL.TXT
	$(PYTHON) setup.py -q sdist --format=gztar
	$(PYTHON) setup.py -q sdist --format=zip
	$(PYTHON) setup.py -q bdist --format=rpm
	$(PYTHON) setup.py -q bdist --format=wininst

docdist: doc
	find doc -print | egrep -v '.svn' | zip dist/nltk_lite-doc-$(NLTK_VERSION).zip -@

exampledist: doc
	find examples -print | egrep -v '.svn' | zip dist/nltk_lite-examples-$(NLTK_VERSION).zip -@

corporadist:
	find corpora -print | egrep -v '.svn' | zip dist/nltk_lite-corpora-$(NLTK_VERSION).zip -@

# Get the version number.
INSTALL.TXT: INSTALL.TXT.in
	cat $< | sed "s/??\.??/$(NLTK_VERSION)/g" >$@

########################################################################
# ISO Image
########################################################################

.PHONY: iso python wordnet numpy
.PHONY: .python.done .rsync.done .wordnet.done .numpy.done

SFNETMIRROR = http://superb-west.dl.sourceforge.net/sourceforge
PYTHON25 = http://www.python.org/ftp/python/2.5
NUMPY = $(SFNETMIRROR)/numpy
WN21 = http://wordnet.princeton.edu/2.1/

python:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac/  $(PYTHON25)/python-2.5-macosx.dmg
	wget -N -P python/win/  $(PYTHON25)/python-2.5.msi
	wget -N -P python/unix/ $(PYTHON25)/Python-2.5.tgz
	touch .python.done

numpy:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/win/  $(NUMPY)/numpy-1.0.win32-py2.5.exe?download
	wget -N -P python/unix/ $(NUMPY)/numpy-1.0.tar.gz?download
	mv python/win/numpy-1.0.win32-py2.5.exe?download python/win/numpy-1.0.win32-py2.5.exe
	mv python/unix/numpy-1.0.tar.gz?download python/unix/numpy-1.0.tar.gz
	cp python/unix/numpy-1.0.tar.gz python/mac/numpy-1.0.tar.gz
	touch .numpy.done

wordnet:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac/  $(WN21)/WordNet-2.1.tar.gz
	wget -N -P python/win/  $(WN21)/WordNet-2.1.exe
	cp python/mac/WordNet-2.0.tar.gz python/unix
	touch .wordnet.done

iso:	.dist.done .python.done .numpy.done .wordnet.done .pywordnet.done
	rm -rf iso nltk_lite-$(NLTK_VERSION)
	mkdir -p iso/web iso/web/screenshots/ iso/mac iso/win iso/unix
	cp dist/nltk_lite-$(NLTK_VERSION).tar.gz	iso/mac/
	cp dist/nltk_lite-$(NLTK_VERSION).win32.exe	iso/win/
	cp dist/nltk_lite-$(NLTK_VERSION).tar.gz	iso/unix/
	cp dist/nltk_lite-$(NLTK_VERSION)-1.noarch.rpm	iso/unix/
	cp dist/nltk_lite-corpora-$(NLTK_VERSION).zip	iso
	cp dist/nltk_lite-doc-$(NLTK_VERSION).zip	iso
	cp *.txt *.TXT					iso
	cp web/*.{html,css,png}                         iso/web/
	cp web/screenshots/*.jpg                        iso/web/screenshots
	cp python/mac/*                                 iso/mac/
	cp python/win/*                                 iso/win/
	cp python/unix/*                                iso/unix/
	ln -f -s iso nltk_lite-$(NLTK_VERSION)
	mkisofs -f -r -o dist/nltk_lite-$(NLTK_VERSION).iso nltk_lite-$(NLTK_VERSION)

########################################################################
# RSYNC
########################################################################

.PHONY: rsync

WEB = stevenbird@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs/lite
RSYNC_OPTS = -arvz -e ssh --relative --cvs-exclude

rsync:	clean_up
	$(MAKE) -C web rsync
	$(MAKE) -C doc rsync
	rsync $(RSYNC_OPTS) nltk_lite $(WEB)
	touch .rsync.done

########################################################################
# CLEAN
########################################################################

.PHONY: clean clean_up

clean:	clean_up
	rm -rf build iso dist
	$(MAKE) -C doc clean

clean_up: clean_code
	$(MAKE) -C doc clean_up

clean_code:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	rm -f `find . -name '*~'`
