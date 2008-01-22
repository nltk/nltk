# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2008 University of Pennsylvania
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

__all__ = [
    # Tagger interface
    'TaggerI',
    
    # Should these be included:?
    #'SequentialBackoffTagger', 'ContextTagger',

    # Sequential backoff taggers.
    'DefaultTagger', 'UnigramTagger', 'BigramTagger', 'TrigramTagger',
    'NgramTagger', 'AffixTagger', 'RegexpTagger',

    # Brill tagger -- trainer names?
    'BrillTagger', 'BrillTaggerTrainer', 'FastBrillTaggerTrainer',

    # Utilities.  Note: conversion functions x2y are intentionally
    # left out; they should be accessed as nltk.tag.x2y().  Similarly
    # for nltk.tag.accuracy.
    'untag', 
    ]

# Import hmm module if numpy is installed
try:
    import numpy
    from hmm import *
    __all__ += ['HiddenMarkovModelTagger', 'HiddenMarkovModelTrainer',]
    # [xx] deprecated HiddenMarkovModel etc objects?
except ImportError:
    pass


######################################################################
#{ Deprecated
######################################################################
from nltk.internals import Deprecated
class TagI(TaggerI, Deprecated):
    """Use nltk.TaggerI instead."""
class SequentialBackoff(SequentialBackoffTagger, Deprecated):
    """Use nltk.SequentialBackoffTagger instead.  Note: the methods
    used to subclass SequentialBackoffTagger do not match those of
    the old nltk.tag.SequentialBackoff; see the api docs for info."""
class Ngram(SequentialBackoffTagger, Deprecated):
    """Use nltk.NgramTagger instead.  Note: NgramTagger.train() is now
    a factory method."""
    def __init__(self, n, cutoff=1, backoff=None):
        SequentialBackoffTagger.__init__(self, backoff)
        self._cutoff = cutoff
        self._n = n
    def train(self, tagged_corpus, verbose=False):
        self._tagger = NgramTagger.train(
            tagged_corpus, self._n, self.backoff, self._cutoff, verbose)
    def choose_tag(self, tokens, index, history):
        return self._tagger.choose_tag(tokens, index, history)
class Unigram(Ngram, Deprecated):
    """Use nltk.UnigramTagger instead."""
    def __init__(self, cutoff=1, backoff=None):
        Ngram.__init__(self, 1, cutoff, backoff)
class Bigram(Ngram, Deprecated):
    """Use nltk.BigramTagger instead."""
    def __init__(self, cutoff=1, backoff=None):
        Ngram.__init__(self, 2, cutoff, backoff)
class Trigram(Ngram, Deprecated):
    """Use nltk.TrigramTagger instead."""
    def __init__(self, cutoff=1, backoff=None):
        Ngram.__init__(self, 3, cutoff, backoff)
class Affix(SequentialBackoffTagger, Deprecated):
    """Use nltk.AffixTagger instead."""
    def __init__(self, length, minlength, backoff=None):
        SequentialBackoffTagger.__init__(self, backoff)
        self._len = length
        self._minlen = minlength
        self._cutoff = cutoff
    def train(self, tagged_corpus):
        self._tagger = AffixTagger.train(
            tagged_corpus, self._minlen, self._len, self.backoff)
    def choose_tag(self, tokens, index, history):
        return self._tagger.choose_tag(tokens, index, history)
class Lookup(UnigramTagger, Deprecated):
    """Use UnigramTagger instead."""
class Regexp(RegexpTagger, Deprecated):
    """Use RegexpTagger instead."""

    
    
