#
# NLP Toolkit main Makefile
# Edward Loper
#
# Created [05/24/01 11:34 PM]
#

##############################################
##  User commands

all: _src _webpage

help:
	# Usage:
	#     make [all | documentation | source | clean | help]

source: _src

documentation: _doc

# A clean source tree is a happy source tree.
clean:
	$(MAKE) -C doc clean
	$(MAKE) -C psets clean
	$(MAKE) -C src clean
	$(MAKE) -C html clean
	rm -rf webpage

##############################################
##  Config

HOST = gradient.cis.upenn.edu
HOSTWWW = ~/public_html/nltk2
HOSTFILE = webpage

##############################################
##  Internal makefile rules

# Make the documentation
_doc:
	$(MAKE) -C doc pdf

# Make the problem sets
_pset:

# Make the html files
_html:

# Make the source distributions
_src:

##############################################
##  Web page rules

# Construct a tarball from the webpage
webpage.tgz: _webpage
	tar -cvzf webpage.tgz webpage

# Transfer the web page to host.
# ssh .identity must be set up correctly for this to work.
xfer: webpage.tgz
	scp webpage.tgz $(HOST):$(HOSTFILE).tgz
	ssh $(HOST) \
            "(rm -f $(HOSTFILE).tar && \
             gunzip $(HOSTFILE).tgz && \
             tar -xvf $(HOSTFILE).tar && \
             (mv -f $(HOSTWWW) $(HOSTWWW).backup || true) && \
             mv webpage $(HOSTWWW)) && \
             rm $(HOSTFILE).tar"

# Construct the web page for the toolkit.
_webpage: _doc _pset _html _src
	rm -rf webpage
	mkdir webpage
	cp html/*.html webpage 2>/dev/null || true
	mkdir webpage/tutorial
	cp doc/tutorial/*/*.ps webpage/tutorial 2>/dev/null || true
	cp doc/tutorial/*/*.pdf webpage/tutorial 2>/dev/null || true
	cp html/tutorial/*.html webpage/tutorial 2>/dev/null || true

	mkdir webpage/tech
	cp html/tech/*.html webpage/tech 2>/dev/null || true
	cp doc/tech/*/*.ps webpage/tech 2>/dev/null || true
	cp doc/tech/*/*.pdf webpage/tech 2>/dev/null || true

	mkdir webpage/psets
	cp html/psets/*.html webpage/psets 2>/dev/null || true
	cp psets/*/*.ps webpage/psets 2>/dev/null || true
	cp psets/*/*.pdf webpage/psets 2>/dev/null || true

	mkdir webpage/src
	cp html/src/*.html webpage/src 2>/dev/null || true
	cp src/nltk.tgz webpage/src 2>/dev/null || true
	cp src/nltk.zip webpage/src 2>/dev/null || true
	cp src/nltk.exe webpage/src 2>/dev/null || true
	cp src/nltk.rpm webpage/src 2>/dev/null || true

	mkdir webpage/ref
	cp html/ref/*.html webpage/ref 2>/dev/null || true
# Make the ref docs!
