# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This package contains several *tokenizers*, which break continuous text
into a sequence of units, such as words and punctuation.  Tokenizers operate on a string,
and return a sequence of strings, one per token.  The decision about which
tokenizer to use often depends on the particular application.

The most frequently used tokenizer is ``word_tokenize()``, e.g.

    >>> word_tokenize("Good muffins cost $3.88 in New York.)
    ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.']

For more information about tokenization, please see the tokenizer HOWTO,
or chapter 3 of the NLTK book.
"""

from nltk.data import load 

from .simple import *
from .regexp import *
from .punkt import *
from .sexpr import *
from .treebank import *

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
    from .texttiling import *
    __all__ += ['TextTilingTokenizer']


# Standard sentence tokenizer.
def sent_tokenize(text):
    """
    Return a sentence-tokenized copy of *text*,
    using NLTK's recommended sentence tokenizer
    (currently :class:`.PunktSentenceTokenizer`).
    """
    tokenizer = load('tokenizers/punkt/english.pickle')
    return tokenizer.tokenize(text)
    
# Standard word tokenizer.
_word_tokenize = TreebankWordTokenizer().tokenize
def word_tokenize(text):
    """
    Return a tokenized copy of *text*,
    using NLTK's recommended word tokenizer
    (currently :class:`.TreebankWordTokenizer`).
    This tokenizer is designed to work on a sentence at a time.
    """
    return _word_tokenize(text)
