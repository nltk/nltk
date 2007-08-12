# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for tagging each token of a sentence with
supplementary information, such as its part of speech.  This task,
which is known as X{tagging}, is defined by the L{TaggerI} interface.
"""

from api import *
from util import *
#from unigram import *
#from ngram import *
from sequential import *
from brill import *

# Import hmm module if numpy is installed

try:
    import numpy
    from hmm import *
except ImportError:
    pass

# # Deprecated:
# from nltk.utilities import Deprecated
# class TagI(TaggerI, Deprecated):
#     'Use nltk.TaggerI instead.'
# class SequentialBackoff(SequentialBackoffTagger, Deprecated):
#     'Use nltk.SequentialBackoffTagger instead.'
# class Unigram(Deprecated, SequentialBackoffTagger):
#     """Use nltk.UnigramTagger instead.  Note: UnigramTagger.train()
#     is now a static method."""
#     def __init__(self, cutoff=1, backoff=None):
#         self._cutoff = cutoff
#         self._backoff = backoff
#         self._tagger = None
#     def train(self, tagged_corpus, verbose=False):
#         self._tagger = UnigramTagger.train(tagged_corpus, verbose)
#class LookupTagger(UnigramTagger, Deprecated):
#    'Use UnigramTagger instead.'

    
    
