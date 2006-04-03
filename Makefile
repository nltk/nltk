# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#	 Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Python executable
PYTHON = python

# Get the version of nltk
NLTK_VERSION=$(shell python -c 'import nltk_lite; print nltk_lite.__version__')

# CVS snapshot build directory
DATE = $(shell date +%F)
CVS_SNAPSHOT = nltk_lite_$(DATE)

# Sourceforge mirror
SFNETMIRROR = http://optusnet.dl.sourceforge.net/sourceforge

.PHONY: all usage help doc documentation webpage test
.PHONY: distributions clean iso python .python.done tgz

all: distributions

usage:
	@echo "make distributions -- Build distributions (output to dist/)"
	@echo "make test -- Run unit tests"
	@echo "make checkdocs -- Check docstrings for completeness"
	@echo "make clean -- Remove temporary and built files"

# Tests.
test: 
	$(PYTHON) runtests.py -v -c coverage

clean:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	$(MAKE) -C doc clean
	rm -rf build dist MANIFEST

# Distributions. Build all from scratch.
distributions: clean sdist bdist docdist corporadist

# Source distributions
sdist: gztardist zipdist

# Built distributions
bdist: rpmdist windist

# Produce dist/$(NAME)-$(VERSION).tar.gz
gztardist: INSTALL.TXT
	python setup.py -q sdist --format=gztar

# Produce dist/$(NAME)-$(VERSION).tar.gz
zipdist: INSTALL.TXT
	python setup.py -q sdist --format=zip

# Produce dist/$(NAME)-$(VERSION)-1.noarch.rpm
# Produce dist/$(NAME)-$(VERSION)-1.src.rpm
rpmdist: INSTALL.TXT
	python setup.py -q bdist --format=rpm

# Produce dist/$(NAME)-$(VERSION).win32.exe
windist: INSTALL.TXT
	python setup.py -q bdist --format=wininst

docdist:
	$(MAKE) -C doc all
	zip -r dist/nltk_lite-doc-$(NLTK_VERSION).zip doc -x CVS
#	tar czvf tutorials.tgz --exclude=CVS --exclude==api doc

corporadist:
	zip -r dist/nltk_lite-corpora-$(NLTK_VERSION).zip corpora -x CVS
#	tar czvf corpora.tgz --exclude=CVS corpora

# Automatically add the appropriate version number.
INSTALL.TXT: INSTALL.TXT.in
	cat $< | sed "s/??\.??/$(NLTK_VERSION)/g" >$@

# CVS snapshot
tgz:
	echo "build apidocs and tutorials manually"
	rm -rf $(CVS_SNAPSHOT)
	cvs -d:ext:stevenbird@cvs.sourceforge.net:/cvsroot/nltk co nltk/lite
	mv nltk $(CVS_SNAPSHOT)
#	cp -r doc/api $(CVS_SNAPSHOT)/lite/doc/api
	cp doc/en/*.html $(CVS_SNAPSHOT)/lite/doc/en
	tar cvzf $(CVS_SNAPSHOT).tgz $(CVS_SNAPSHOT)

python:	.python.done
	mkdir -p iso/{mac,win,unix}
	wget -N -O iso/mac/MacPython-OSX-2.4.1-1.dmg http://undefined.org/python/MacPython-OSX-2.4.1-1.dmg
	wget -N -O iso/mac/numarray-1.1.1-py2.4-macosx10.3.zip http://www.pythonmac.org/packages/numarray-1.1.1-py2.4-macosx10.3.zip
	wget -N -O iso/win/Python-2.4.2.msi http://www.python.org/ftp/python/2.4.2/python-2.4.2.msi
	wget -N -O iso/win/numarray-1.5.0.exe $(SFNETMIRROR)/numpy/numarray-1.5.0.win32-py2.4.exe?download
	wget -N -O iso/unix/Python-2.4.2.tgz http://www.python.org/ftp/python/2.4.2/Python-2.4.2.tgz
	wget -N -O iso/unix/numarray-1.5.0.tar.gz $(SFNETMIRROR)/numpy/numarray-1.5.0.tar.gz?download
	touch .python.done

iso:	dist
	echo "get Python distro?"
	rm -rf iso/webpage iso/nltk* iso/*/nltk*
	mkdir -p iso/webpage iso/webpage/screenshots/
	cp dist/nltk_lite-$(NLTK_VERSION).tar.gz	iso/mac/
	cp dist/nltk_lite-$(NLTK_VERSION).win32.exe	iso/win/
	cp dist/nltk_lite-$(NLTK_VERSION).tar.gz	iso/unix/
	cp dist/nltk_lite-$(NLTK_VERSION)-1.noarch.rpm	iso/unix/
	cp dist/nltk_lite-corpora-$(NLTK_VERSION).zip	iso
	cp dist/nltk_lite-doc-$(NLTK_VERSION).zip	iso
	cp *.txt *.TXT					iso
	cp ../doc/webpage/*.{html,css,png}              iso/webpage/
	cp ../doc/webpage/screenshots/*.jpg             iso/webpage/screenshots
	ln -f -s iso/ nltk_lite-$(NLTK_VERSION)
	mkisofs -f -r -o dist/nltk_lite-$(NLTK_VERSION).iso nltk_lite-$(NLTK_VERSION)
