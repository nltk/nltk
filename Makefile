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
# DISTRIBUTIONS
########################################################################

.PHONY: dist codedist docdist corporadist .dist.done

dist: codedist docdist exampledist corporadist
	touch .dist.done

codedist: clean_code INSTALL.TXT
	python setup.py -q sdist --format=gztar
	python setup.py -q sdist --format=zip
	python setup.py -q bdist --format=rpm
	python setup.py -q bdist --format=wininst

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

.PHONY: iso python wordnet pywordnet numarray
.PHONY: .python.done .rsync.done .wordnet.done .pywordnet .numarray.done

SFNETMIRROR = http://superb-west.dl.sourceforge.net/sourceforge
PYTHON = http://www.python.org/ftp/python/2.5
PYTHON24 = http://www.python.org/ftp/python/2.4.3
NUMPY = $(SFNETMIRROR)/numpy
MACPY = http://www.pythonmac.org/packages
WN20 = http://wordnet.princeton.edu/2.0/

python:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac/  $(PYTHON24)/Universal-MacPython-2.4.3.dmg
	wget -N -P python/win/  $(PYTHON)/python-2.5.msi
	wget -N -P python/unix/ $(PYTHON)/Python-2.5.tgz
	touch .python.done

numarray:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac/  $(MACPY)/py24-fat/mpkg/numarray-1.5.1-py2.4-macosx10.4.mpkg.zip
	wget -N -P python/win/  $(NUMPY)/numarray-1.5.2.win32-py2.5.exe?download
	wget -N -P python/unix/ $(NUMPY)/numarray-1.5.2.tar.gz?download
	mv python/win/numarray-1.5.2.win32-py2.5.exe?download python/win/numarray-1.5.2.win32-py2.5.exe
	mv python/unix/numarray-1.5.2.tar.gz?download python/unix/numarray-1.5.2.tar.gz
	touch .numarray.done

wordnet:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac/  $(WN20)/WordNet-2.0.tar.gz
	wget -N -P python/win/  $(WN20)/WordNet-2.0.exe
	cp python/mac/WordNet-2.0.tar.gz python/unix
	touch .wordnet.done

pywordnet:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac/  $(SFNETMIRROR)/pywordnet/pywordnet-2.0.1.tar.gz?download
	wget -N -P python/win/  $(SFNETMIRROR)/pywordnet/pywordnet-2.0.1.win32.exe?download
	mv python/mac/pywordnet-2.0.1.tar.gz?download python/mac/pywordnet-2.0.1.tar.gz
	mv python/win/pywordnet-2.0.1.win32.exe?download python/win/pywordnet-2.0.1.win32.exe
	cp python/mac/pywordnet-2.0.1.tar.gz python/unix
	touch .pywordnet.done

iso:	.dist.done .python.done .numarray.done .wordnet.done .pywordnet.done
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
