# Natural Language Toolkit: Tokenizer Utilities
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

from re import finditer

def string_span_tokenize(s, sep):
    r"""
    Return the offsets of the tokens in *s*, as a sequence of ``(start, end)``
    tuples, by splitting the string at each occurrence of *sep*.

        >>> from nltk.tokenize.util import string_span_tokenize
        >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
        ... two of them.\n\nThanks.'''
        >>> list(string_span_tokenize(s, " "))
        [(0, 4), (5, 12), (13, 17), (18, 26), (27, 30), (31, 36), (37, 37),
        (38, 44), (45, 48), (49, 55), (56, 58), (59, 73)]

    :param s: the string to be tokenized
    :type s: str
    :param sep: the token separator
    :type sep: str
    :rtype: iter(tuple(int, int))
    """
    if len(sep) == 0:
        raise ValueError("Token delimiter must not be empty")
    left = 0
    while True:
        try:
            right = s.index(sep, left)
            if right != 0:
                yield left, right
        except ValueError:
            if left != len(s):
                yield left, len(s)
            break

        left = right + len(sep)

def regexp_span_tokenize(s, regexp):
    r"""
    Return the offsets of the tokens in *s*, as a sequence of ``(start, end)``
    tuples, by splitting the string at each successive match of *regexp*.

        >>> from nltk.tokenize import WhitespaceTokenizer
        >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
        ... two of them.\n\nThanks.'''
        >>> list(WhitespaceTokenizer().span_tokenize(s))
        [(0, 4), (5, 12), (13, 17), (18, 23), (24, 26), (27, 30), (31, 36),
        (38, 44), (45, 48), (49, 51), (52, 55), (56, 58), (59, 64), (66, 73)]

    :param s: the string to be tokenized
    :type s: str
    :param regexp: regular expression that matches token separators
    :type regexp: str
    :rtype: iter(tuple(int, int))
    """
    left = 0
    for m in finditer(regexp, s):
        right, next = m.span()
        if right != 0:
            yield left, right
        left = next
    yield left, len(s)

def spans_to_relative(spans):
    r"""
    Return a sequence of relative spans, given a sequence of spans.

        >>> from nltk.tokenize import WhitespaceTokenizer
        >>> from nltk.tokenize.util import spans_to_relative
        >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
        ... two of them.\n\nThanks.'''
        >>> list(spans_to_relative(WhitespaceTokenizer().span_tokenize(s)))
        [(0, 4), (1, 7), (1, 4), (1, 5), (1, 2), (1, 3), (1, 5), (2, 6),
        (1, 3), (1, 2), (1, 3), (1, 2), (1, 5), (2, 7)]

    :param spans: a sequence of (start, end) offsets of the tokens
    :type spans: iter(tuple(int, int))
    :rtype: iter(tuple(int, int))
    """
    prev = 0
    for left, right in spans:
        yield left - prev, right - left
        prev = right


