# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for tagging each token of a document with
supplementary information, such as its part of speech or its WordNet
synset tag.  This task, which is known as X{tagging}, is defined by
the L{TagI} interface.
"""

from api import *
from util import *
from unigram import *
from ngram import *
from brill import *

# Import hmm module if numpy is installed

try:
    import numpy
    from hmm import *
except ImportError:
    pass
