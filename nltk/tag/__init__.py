# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for tagging each token of a sentence with
supplementary information, such as its part of speech.  This task,
which is known as X{tagging}, is defined by the L{TaggerI} interface.
"""

from api import *
from util import *
from simplify import *
from sequential import *
from brill import *
from tnt import *
from hunpos import *
from stanford import *
import nltk

__all__ = [
    # Tagger interface
    'TaggerI',

    # Standard POS tagger
    'pos_tag', 'batch_pos_tag',
    
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

# Standard treebank POS tagger
_POS_TAGGER = 'taggers/maxent_treebank_pos_tagger/english.pickle'
def pos_tag(tokens):
    """
    Use NLTK's currently recommended part of speech tagger to
    tag the given list of tokens.
    """
    tagger = nltk.data.load(_POS_TAGGER)
    return tagger.tag(tokens)

def batch_pos_tag(sentences):
    """
    Use NLTK's currently recommended part of speech tagger to tag the
    given list of sentences, each consisting of a list of tokens.
    """
    tagger = nltk.data.load(_POS_TAGGER)
    return tagger.batch_tag(sentences)
