# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Functions for X{tokenizing}, i.e., dividing text strings into
substrings.
"""

from simple import *
from regexp import *
from punkt import *
from sexpr import *
from treebank import *
from nltk.internals import deprecated
import nltk

__all__ = ['WhitespaceTokenizer', 'SpaceTokenizer', 'TabTokenizer',
           'LineTokenizer', 'RegexpTokenizer', 'BlanklineTokenizer',
           'WordPunctTokenizer', 'WordTokenizer', 'blankline_tokenize',
           'wordpunct_tokenize', 'regexp_tokenize', 'word_tokenize',
           'SExprTokenizer', 'sexpr_tokenize', 'line_tokenize',
           'PunktWordTokenizer', 'PunktSentenceTokenizer',
           'TreebankWordTokenizer', 'sent_tokenize', 'word_tokenize'
           ]

# Standard sentence tokenizer.
def sent_tokenize(text):
    """
    Use NLTK's currently recommended sentence tokenizer to tokenize
    sentences in the given text.  Currently, this uses
    L{PunktSentenceTokenizer}.
    """
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    return tokenizer.tokenize(text)
    
# Standard word tokenizer.
_word_tokenize = TreebankWordTokenizer().tokenize
def word_tokenize(text):
    """
    Use NLTK's currently recommended word tokenizer to tokenize words
    in the given sentence.  Currently, this uses
    L{TreebankWordTokenizer}.  This tokenizer should be fed a single
    sentence at a time.
    """
    return _word_tokenize(text)

######################################################################
#{ Deprecated since 0.8
######################################################################

@deprecated("Use nltk.blankline_tokenize() or "
            "nltk.BlanklineTokenizer instead.")
def blankline(text):
    return BlanklineTokenizer().tokenize(text)

@deprecated("Use nltk.wordpunct_tokenize() or "
            "nltk.WordPunctTokenizer instead.")
def wordpunct(text):
    return WordPunctTokenizer().tokenize(text)

@deprecated("Use str.split() or nltk.WhitespaceTokenizer instead.")
def whitespace(text):
    return WhitespaceTokenizer().tokenize(text)

@deprecated("Use nltk.word_tokenize() or "
            "nltk.WordTokenizer instead.")
def word(text):
    return WordTokenizer().tokenize(text)

@deprecated("Use nltk.line_tokenize() or "
            "nltk.LineTokenizer instead.")
def line(text):
    return LineTokenizer().tokenize(text)

@deprecated("Use method of nltk.tokenize.PunktWordTokenizer "
            "instead.")
def punkt_word_tokenize(text):
    return PunktWordTokenizer().tokenize(text)

#}

