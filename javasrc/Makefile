# Natural Language Toolkit: java interface code Makefile
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Dependencies.
MALLET_HOME = /usr/local/mallet-0.4

# Locate the NLTK java source code
JAVA_SRC = $(shell find org/nltk -name '*.java')
JAVA_CLS = $(JAVA_SRC:.java=.class)

# Set up java.
JAVAC=javac
CLASSPATH = .:$(MALLET_HOME)/class/:$(MALLET_HOME)/lib/mallet-deps.jar:$(MALLET_HOME)/lib/mallet.jar

########################################################################
# Targets
########################################################################

.PHONY: find-mallet javac clean jar jar2

jar: find-mallet nltk.jar

find-mallet:
	@if [ -d $(MALLET_HOME) ]; then \
		echo "Found Mallet: $(MALLET_HOME)"; \
	else \
		echo; \
		echo "Unable to locate required Mallet dependencies.  Use:"; \
		echo "    make MALLET_HOME=/path/to/mallet [target...]"; \
		echo "to specify the location of Mallet.  Mallet can be "; \
		echo "downloaded from http://mallet.cs.umass.edu/"; \
		echo; false; fi

nltk.jar: $(JAVA_SRC)
	$(JAVAC) -cp "$(CLASSPATH)" $(JAVA_SRC)
	jar -cf nltk.jar `find org/nltk -name '*.class'`

clean:
	rm -f $(JAVA_CLS) nltk.jar
