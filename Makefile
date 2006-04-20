# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#	 Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

PYTHON = python
NLTK_VERSION = $(shell python -c 'import nltk_lite; print nltk_lite.__version__')
#SFNETMIRROR = http://optusnet.dl.sourceforge.net/sourceforge
SFNETMIRROR = http://easynews.dl.sourceforge.net/sourceforge
WEB = stevenbird@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs/lite
RSYNC_OPTS = -arvz -e ssh --relative --cvs-exclude

.PHONY: all usage help doc rsync
.PHONY: clean clean_up iso python wordnet
.PHONY: .python.done .doc.done .rsync.done
.PHONY: distributions codedist docdist corporadist

usage:
	@echo "make distributions -- Build distributions (output to dist/)"
	@echo "make python -- Fetch Python distributions"
	@echo "make rsync -- Upload files to NLTK website"
	@echo "make clean -- Remove all built files and temporary files"
	@echo "make clean_up -- Remove temporary files"

all: distributions

doc:	.doc.done
	$(MAKE) -C doc all
	touch .doc.done

########################################################################
# DISTRIBUTIONS
########################################################################

# Distributions. Build all from scratch.
distributions: codedist docdist corporadist

codedist: clean INSTALL.TXT
	python setup.py -q sdist --format=gztar
	python setup.py -q sdist --format=zip
	python setup.py -q bdist --format=rpm
	python setup.py -q bdist --format=wininst

docdist:	.doc.done
	zip -r dist/nltk_lite-doc-$(NLTK_VERSION).zip doc -x .svn

corporadist:
	zip -r dist/nltk_lite-corpora-$(NLTK_VERSION).zip corpora -x .svn

# Get the version number.
INSTALL.TXT: INSTALL.TXT.in
	cat $< | sed "s/??\.??/$(NLTK_VERSION)/g" >$@

########################################################################
# ISO Image
########################################################################

python:	.python.done
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac/  http://www.python.org/ftp/python/2.4.3/Universal-MacPython-2.4.3.dmg
	wget -N -P python/mac/  http://www.pythonmac.org/packages/numarray-1.1.1-py2.4-macosx10.3.zip
	wget -N -P python/mac/  http://wordnet.princeton.edu/2.0/WordNet-2.0.tar.gz
	wget -N -P python/win/  http://www.python.org/ftp/python/2.4.3/python-2.4.3.msi
	wget -N -P python/win/  $(SFNETMIRROR)/numpy/numarray-1.5.1.win32-py2.4.exe?download
	wget -N -P python/unix/ http://www.python.org/ftp/python/2.4.3/Python-2.4.3.tgz
	wget -N -P python/unix/ $(SFNETMIRROR)/numpy/numarray-1.5.1.tar.gz?download
	touch .python.done

wordnet:	.wordnet.done
	wget -N -P python/mac/  $(SFNETMIRROR)/pywordnet/pywordnet-2.0.1.tar.gz?download
	wget -N -P python/win/  $(SFNETMIRROR)/pywordnet/pywordnet-2.0.1.win32.exe?download
	wget -N -P python/win/  http://wordnet.princeton.edu/2.0/WordNet-2.0.exe
	cp python/mac/pywordnet-2.0.1.tar.gz python/mac/WordNet-2.0.tar.gz python/unix
	touch .wordnet.done

iso:	distributions .python.done .wordnet.done
	rm -rf iso
	mkdir -p iso/webpage iso/webpage/screenshots/
	cp dist/nltk_lite-$(NLTK_VERSION).tar.gz	iso/mac/
	cp dist/nltk_lite-$(NLTK_VERSION).win32.exe	iso/win/
	cp dist/nltk_lite-$(NLTK_VERSION).tar.gz	iso/unix/
	cp dist/nltk_lite-$(NLTK_VERSION)-1.noarch.rpm	iso/unix/
	cp dist/nltk_lite-corpora-$(NLTK_VERSION).zip	iso
	cp dist/nltk_lite-doc-$(NLTK_VERSION).zip	iso
	cp *.txt *.TXT					iso
	cp web/*.{html,css,png}                         iso/web/
	cp web/screenshots/*.jpg                        iso/web/screenshots
	ln -f -s iso/ nltk_lite-$(NLTK_VERSION)
	mkisofs -f -r -o dist/nltk_lite-$(NLTK_VERSION).iso nltk_lite-$(NLTK_VERSION)

########################################################################
# RSYNC
########################################################################

rsync:	.rsync.done clean_up
	$(MAKE) -C web rsync
	$(MAKE) -C doc rsync
       	rsync $(RSYNC_OPTS) nltk_lite $(WEB)/nltk_lite
	touch .rsync.done

########################################################################
# CLEAN
########################################################################

clean:	clean_up
	rm -rf build iso distributions .*.done
	$(MAKE) -C doc clean

clean_up:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	rm -f `find . -name '*~'`
	$(MAKE) -C doc clean_up

