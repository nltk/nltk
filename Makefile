#
# NLP Toolkit main Makefile
# Edward Loper
#
# Created [05/24/01 11:34 PM]
#

all: documentation test distributions

help:
	# Usage:
	#     make [all | documentation | distributions | test | clean]

documentation:
	$(MAKE) -C doc
	$(MAKE) -C psets

test:
	$(MAKE) -C src test

distributions:
	$(MAKE) -C src distributions

clean:
	$(MAKE) -C doc clean
	$(MAKE) -C psets clean
	$(MAKE) -C src clean
