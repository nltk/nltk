# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2007 University of Pennsylvania
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

__all__ = ['WhitespaceTokenizer', 'SpaceTokenizer', 'TabTokenizer',
           'LineTokenizer', 'RegexpTokenizer', 'BlanklineTokenizer',
           'WordPunctTokenizer', 'WordTokenizer', 'blankline_tokenize',
           'wordpunct_tokenize', 'regexp_tokenize', 'word_tokenize',
           'SExprTokenizer', 'sexpr_tokenize',
           'PunktWordTokenizer', 'punkt_word_tokenize',
           'PunktSentenceTokenizer',
           ]

# backwards compatibility: Remove these once we've deprecated
# tokenize.blankline and friends.
blankline = BlanklineTokenizer().tokenize
wordpunct = WordPunctTokenizer().tokenize
whitespace = WhitespaceTokenizer().tokenize
word = WordTokenizer().tokenize
line = LineTokenizer().tokenize

