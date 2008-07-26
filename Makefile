# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#	 Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: http://nltk.org/
# For license information, see LICENSE.TXT

PYTHON = python
NLTK_VERSION = $(shell python -c 'import nltk; print nltk.__version__')
NLTK_URL = $(shell python -c 'import nltk; print nltk.__url__')

.PHONY: usage all doc clean clean_code clean_up

usage:
	@echo "make dist -- Build distributions (output to dist/)"
	@echo "make python -- Fetch Python distributions"
	@echo "make rsync -- Upload files to NLTK website"
	@echo "make clean -- Remove all built files and temporary files"
	@echo "make clean_up -- Remove temporary files"

all: dist

upload:
	rsync -avP -e ssh dist/* $(USER)@frs.sourceforge.net:uploads/

doc:
	$(MAKE) -C doc all

contribdoc:
	$(MAKE) -C doc_contrib all

########################################################################
# TESTING
########################################################################

DOCTEST_DRIVER = nltk/test/doctest_driver.py
DOCTEST_FLAGS = --ellipsis --normalize_whitespace
DOCTEST_FILES = nltk/test/*.doctest nltk/test/*.doctest_latin1

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

.PHONY: dist codedist docdist datadist exampledist .dist.done

dist: codedist docdist exampledist datadist contribdocdist
	touch .dist.done

codedist: gztardist zipdist rpmdist wininstdist dmgdist

gztardist: clean_code
	$(PYTHON) setup.py -q sdist --format=gztar
zipdist: clean_code
	$(PYTHON) setup.py -q sdist --format=zip
rpmdist: clean_code
	$(PYTHON) setup.py -q bdist --format=rpm
wininstdist: clean_code
	$(PYTHON) setup.py -q bdist --format=wininst
dmgdist:
	$(MAKE) -C tools/mac

docdist:
	find doc -print | egrep -v '.svn' | zip dist/nltk-doc-$(NLTK_VERSION).zip -@

contribdocdist:
	find doc_contrib -print | egrep -v '.svn' | zip dist/nltk-contribdoc-$(NLTK_VERSION).zip -@

exampledist:
	find examples -print | egrep -v '.svn' | zip dist/nltk-examples-$(NLTK_VERSION).zip -@

datadist:
	find data -print | egrep -v '.svn' | zip dist/nltk-data-$(NLTK_VERSION).zip -@

nightlydist: codedist
	REVISION = `svn info | grep Revision: | sed "s/Revision: //"`

########################################################################
# ISO Image
########################################################################

.PHONY: iso python numpy pylab
.PHONY: .python.done .rsync.done .numpy.done .pylab.done

SFNET = http://superb-west.dl.sourceforge.net/sourceforge
PYFTP = http://www.python.org/ftp/python/2.5.2
PYMAC = http://pythonmac.org/packages/py25-fat/dmg
NUMPY = $(SFNET)/numpy
PYLAB = $(SFNET)/matplotlib

python:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac  $(PYFTP)/python-2.5.2-macosx.dmg
	wget -N -P python/win  $(PYFTP)/python-2.5.2.msi
	wget -N -P python/unix $(PYFTP)/Python-2.5.2.tgz
	touch .python.done

numpy:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac  $(NUMPY)/numpy-1.1.0-py2.5-macosx10.5.dmg?download
	wget -N -P python/win  $(NUMPY)/numpy-1.1.0-win32-superpack-python2.5.exe?download
	wget -N -P python/unix $(NUMPY)/numpy-1.1.0.tar.gz?download
	mv python/win/numpy-1.1.0-py2.5-macosx10.5.dmg?download python/win/numpy-1.1.0-py2.5-macosx10.5.dmg
	mv python/win/numpy-1.1.0-win32-superpack-python2.5.exe?download python/win/numpy-1.1.0-win32-superpack-python2.5.exe	
	mv python/unix/numpy-1.1.0.tar.gz?download python/unix/numpy-1.1.0.tar.gz
	touch .numpy.done

pylab:
	mkdir -p python/{mac,win,unix}
	wget -N -P python/mac  $(PYMAC)/matplotlib-0.91.1-py2.5-macosx10.4-2007-12-04.dmg
	wget -N -P python/win  $(PYLAB)/matplotlib-0.98.0.win32-py2.5.exe?download
	wget -N -P python/unix $(PYLAB)/matplotlib-0.98.0.tar.gz?download
	mv python/win/matplotlib-0.98.0.win32-py2.5.exe?download python/win/matplotlib-0.98.0.win32-py2.5.exe
	mv python/unix/matplotlib-0.98.0.tar.gz?download python/unix/matplotlib-0.98.0.tar.gz
	touch .pylab.done

prover:	
	wget -N -P python/mac http://www.cs.unm.edu/%7Emccune/prover9/gui/Prover9-Mace4-v05.zip
	wget -N -P python/win http://www.cs.unm.edu/%7Emccune/prover9/gui/Prover9-Mace4-v05-setup.exe
	wget -N -P python/unix http://www.cs.unm.edu/%7Emccune/prover9/gui/p9m4-v05.tar.gz
	mv python/unix/p9m4-v05.tar.gz python/unix/Prover9-Mace4-v05-i386.tar.gz

iso:	.dist.done .python.done .numpy.done .pylab.done
	rm -rf iso nltk-$(NLTK_VERSION)
	mkdir -p iso/{mac,win,unix}
	cp dist/nltk-$(NLTK_VERSION).dmg            iso/mac/
	cp dist/nltk-$(NLTK_VERSION).win32.exe      iso/win/
	cp dist/nltk-$(NLTK_VERSION).tar.gz         iso/unix/
	cp dist/nltk-$(NLTK_VERSION)-1.noarch.rpm   iso/unix/
	cp dist/nltk-data-$(NLTK_VERSION).zip       iso
	cp dist/nltk-doc-$(NLTK_VERSION).zip        iso
	cp dist/nltk-contribdoc-$(NLTK_VERSION).zip iso
	cp dist/nltk-examples-$(NLTK_VERSION).zip   iso
	cp *.txt *.html                             iso
	cp python/mac/*                             iso/mac/
	cp python/win/*                             iso/win/
	cp python/unix/*                            iso/unix/
	ln -f -s iso nltk-$(NLTK_VERSION)
	mkisofs -f -r -o dist/nltk-$(NLTK_VERSION).iso nltk-$(NLTK_VERSION)

########################################################################
# RSYNC
########################################################################

.PHONY: rsync

WEB = $(USER)@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs
RSYNC_OPTS = -lrtvz -e ssh --relative --cvs-exclude

rsync:	clean_up
	$(MAKE) -C doc rsync
	rsync $(RSYNC_OPTS) nltk nltk_contrib examples $(WEB)
	touch .rsync.done

########################################################################
# CLEAN
########################################################################

.PHONY: clean clean_up

clean:	clean_up
	rm -rf build iso dist MANIFEST
	$(MAKE) -C doc clean
	$(MAKE) -C doc_contrib clean
	$(MAKE) -C javasrc clean
	rm -f nltk/nltk.jar

clean_up: clean_code
	$(MAKE) -C doc clean_up

clean_code:
	rm -f `find . -name '*.pyc'`
	rm -f `find . -name '*.pyo'`
	rm -f `find . -name '*~'`
	rm -f MANIFEST # regenerate manifest from MANIFEST.in
