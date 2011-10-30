# Natural Language Toolkit: Tokenizer Utilities
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

from re import finditer

def string_span_tokenize(s, sep):
    """
    Return the offsets of the tokens in *s*, as a sequence of ``(start, end)`` tuples,
    by splitting the string at each occurrence of *sep*.
    
    :param s: the string to be tokenized
    :type s: str
    :param sep: the token separator
    :type sep: str
    :rtype: iter(tuple(int, int))
    """
    if len(sep) == 0:
        raise ValueError, "Token delimiter must not be empty"
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
    """
    Return the offsets of the tokens in *s*, as a sequence of ``(start, end)`` tuples,
    by splitting the string at each successive match of *regexp*.
    
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
    """
    Return a sequence of relative spans, given a sequence of spans.
    
    :param spans: a sequence of (start, end) offsets of the tokens
    :type spans: iter(tuple(int, int))
    :rtype: iter(tuple(int, int))
    """
    prev = 0
    for left, right in spans:
        yield left - prev, right - left
        prev = right
