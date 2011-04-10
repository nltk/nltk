# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
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
import nltk

__all__ = ['WhitespaceTokenizer', 'SpaceTokenizer', 'TabTokenizer',
           'LineTokenizer', 'RegexpTokenizer', 'BlanklineTokenizer',
           'WordPunctTokenizer', 'blankline_tokenize',
           'wordpunct_tokenize', 'regexp_tokenize', 'word_tokenize',
           'SExprTokenizer', 'sexpr_tokenize', 'line_tokenize',
           'PunktWordTokenizer', 'PunktSentenceTokenizer',
           'TreebankWordTokenizer', 'sent_tokenize', 'word_tokenize',
           ]

try: import numpy
except ImportError: pass
else:
    from texttiling import *
    __all__ += ['TextTilingTokenizer']

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
