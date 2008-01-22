# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Functions for X{tokenizing}, i.e., dividing text strings into
substrings.
"""

from simple import *
from regexp import *
from punkt import *
from sexpr import *
from nltk.internals import deprecated

__all__ = ['WhitespaceTokenizer', 'SpaceTokenizer', 'TabTokenizer',
           'LineTokenizer', 'RegexpTokenizer', 'BlanklineTokenizer',
           'WordPunctTokenizer', 'WordTokenizer', 'blankline_tokenize',
           'wordpunct_tokenize', 'regexp_tokenize', 'word_tokenize',
           'SExprTokenizer', 'sexpr_tokenize', 'line_tokenize',
           'PunktWordTokenizer', 'punkt_word_tokenize',
           'PunktSentenceTokenizer',
           ]

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

#}

