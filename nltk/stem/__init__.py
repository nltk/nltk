# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interfaces used to remove morphological affixes from words, leaving
only the word stem.  Stemming algorithms aim to remove those affixes
required for eg. grammatical role, tense, derivational morphology
leaving only the stem of the word.  This is a difficult problem due to
irregular words (eg. common verbs in English), complicated
morphological rules, and part-of-speech and sense ambiguities
(eg. C{ceil-} is not the stem of C{ceiling}).

C{StemmerI} defines a standard interface for stemmers.
"""

from api import *
from regexp import *
from porter import *
from lancaster import *
from wordnet import *
from rslp import *

__all__ = [
    # Stemmer interface
    'StemmerI',

    # Stemmers
    'RegexpStemmer', 'PorterStemmer', 'LancasterStemmer',
    'RSLPStemmer', 'WordNetLemmatizer', 'WordnetStemmer'
    ]

######################################################################
#{ Deprecated
######################################################################
from nltk.internals import Deprecated
class StemI(StemmerI, Deprecated):
    """Use nltk.StemmerI instead."""
class Regexp(RegexpStemmer, Deprecated):
    """Use nltk.RegexpStemmer instead."""
class Porter(PorterStemmer, Deprecated):
    """Use nltk.PorterStemmer instead."""
class Lancaster(LancasterStemmer, Deprecated):
    """Use nltk.LancasterStemmer instead."""
class Wordnet(WordNetStemmer, Deprecated):
    """Use nltk.WordNetLemmatizer instead."""
    
    
