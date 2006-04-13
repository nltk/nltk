# NLTK-LITE: Webpage Makefile
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

WEB = stevenbird@shell.sourceforge.net:/home/groups/n/nl/nltk/htdocs

RSYNC_OPTS = -arvz -e ssh --relative --cvs-exclude

.PHONY: rsync

all: rsync

rsync:
	rsync $(RSYNC_OPTS) . $(WEB)
