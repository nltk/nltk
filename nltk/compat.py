# Natural Language Toolkit: Compatibility Functions
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Backwards compatibility with previous versions of Python.

This module provides backwards compatibility by defining
functions and classes that were not available in earlier versions of
Python.  Intented usage:

    >>> from nltk.compat import *

Currently, NLTK requires Python 2.4 or later.
"""

######################################################################
# New in Python 2.5
######################################################################

# ElementTree

try:
    import ElementTree
except ImportError:
    from nltk.etree import ElementTree

# collections.defaultdict
# contributed by Yoav Goldberg <yoav.goldberg@gmail.com>

try:
    from collections import defaultdict
except ImportError:
    class defaultdict(dict):
        def __init__(self, default_constructor, *rest):
            dict.__init__(self,*rest)
            self.default_constructor = default_constructor

        def __getitem__(self, s):
            try:
                return dict.__getitem__(self, s)
            except KeyError:
                dict.__setitem__(self, s, self.default_constructor())
                return dict.__getitem__(self,s)

