# Natural Language Toolkit: Unit Tests
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit tests for the NLTK modules.  These tests are intented to ensure
that changes that we make to NLTK's code don't accidentally introduce
bugs.

Each module in this package tests a specific aspect of NLTK.  Modules
are typically named for the module or class that they test (e.g.,
L{nltk_lite.test.tree} performs tests on the L{nltk_lite.parse.tree}
module).
"""

import sys, doctest

#######################################################################
# Test runner
#######################################################################



def test(file):
    doctest.testfile(file, optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)

for file in sys.argv[1:]:
    test(file)
