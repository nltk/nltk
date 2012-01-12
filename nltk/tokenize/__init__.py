# -*- coding: utf-8 -*-
# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
NLTK Tokenizer Package

Tokenizers divide strings into lists of substrings.  For example,
tokenizers can be used to find the list of sentences or words in a
string.

    >>> from nltk.tokenize import word_tokenize, wordpunct_tokenize, sent_tokenize
    >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
    ... two of them.\n\nThanks.'''
    >>> wordpunct_tokenize(s)
    ['Good', 'muffins', 'cost', '$', '3', '.', '88', 'in', 'New', 'York', '.',
    'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']
    >>> sent_tokenize(s)
    ['Good muffins cost $3.88\nin New York.', 'Please buy me\ntwo of them.', 'Thanks.']
    >>> [word_tokenize(t) for t in sent_tokenize(s)]
    [['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.'],
    ['Please', 'buy', 'me', 'two', 'of', 'them', '.'], ['Thanks', '.']]

Caution: only use ``word_tokenize()`` on individual sentences.

Caution: when tokenizing a Unicode string, make sure you are not
using an encoded version of the string (it may be necessary to
decode it first, e.g. with ``s.decode("utf8")``.

NLTK tokenizers can produce token-spans, represented as tuples of integers
having the same semantics as string slices, to support efficient comparison
of tokenizers.  (These methods are implemented as generators.)

    >>> from nltk.tokenize import WhitespaceTokenizer
    >>> list(WhitespaceTokenizer().span_tokenize(s))
    [(0, 4), (5, 12), (13, 17), (18, 23), (24, 26), (27, 30), (31, 36), (38, 44),
    (45, 48), (49, 51), (52, 55), (56, 58), (59, 64), (66, 73)]

There are numerous ways to tokenize text.  If you need more control over
tokenization, see the other methods provided in this package.

For further information, please see Chapter 3 of the NLTK book.
"""

from nltk.data              import load
from nltk.tokenize.simple   import (SpaceTokenizer, TabTokenizer, LineTokenizer,
                                    line_tokenize)
from nltk.tokenize.regexp   import (RegexpTokenizer, WhitespaceTokenizer,
                                    BlanklineTokenizer, WordPunctTokenizer,
                                    wordpunct_tokenize, regexp_tokenize,
                                    blankline_tokenize)
from nltk.tokenize.punkt    import PunktSentenceTokenizer, PunktWordTokenizer
from nltk.tokenize.sexpr    import SExprTokenizer, sexpr_tokenize
from nltk.tokenize.treebank import TreebankWordTokenizer

try:
    import numpy
except ImportError:
    pass
else:
    from nltk.tokenize.texttiling import TextTilingTokenizer

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


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
