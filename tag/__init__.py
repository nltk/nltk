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
from sequential import *
from brill import *

# Import hmm module if numpy is installed

try:
    import numpy
    from hmm import *
except ImportError:
    pass

######################################################################
#{ Deprecated
######################################################################
from nltk.utilities import Deprecated
class TagI(TaggerI, Deprecated):
    """Use nltk.TaggerI instead."""
class SequentialBackoff(SequentialBackoffTagger, Deprecated):
    """Use nltk.SequentialBackoffTagger instead.  Note: the methods
    used to subclass SequentialBackoffTagger do not match those of
    the old nltk.tag.SequentialBackoff; see the api docs for info."""
class Ngram(SequentialBackoffTagger, Deprecated):
    """Use nltk.NgramTagger instead.  Note: NgramTagger.train() is now
    a static method."""
    def __init__(self, n, cutoff=1, backoff=None):
        self._n = n
        self._cutoff = cutoff
        self._backoff = backoff
        self._tagger = None
    def train(self, tagged_corpus, verbose=False):
        self._tagger = NgramTagger.train(tagged_corpus, verbose)
    def choose_tag(self, tokens, index, history):
        return self._tagger.choose_tag(tokens, index, history)
class Unigram(Ngram, Deprecated):
    """Use nltk.UnigramTagger instead.  Note: UnigramTagger.train() is
    now a static method."""
class Bigram(Ngram, Deprecated):
    """Use nltk.BigramTagger instead.  Note: BigramTagger.train() is
    now a static method."""
class Trigram(Ngram, Deprecated):
    """Use nltk.TrigramTagger instead.  Note: TrigramTagger.train() is
    now a static method."""
class Lookup(UnigramTagger, Deprecated):
    'Use UnigramTagger instead.'

    
    
