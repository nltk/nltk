# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2010 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

from re import finditer

def string_span_tokenize(s, sep):
    if len(sep) == 0:
        raise ValueError, "Token delimiter must not be empty"
    left = 0
    while True:
        try:
            right = s.index(sep, left)
        except ValueError:
            break

        if right != 0:
            yield left, right
        left = right + len(sep)

def regexp_span_tokenize(s, regexp):
    left = 0
    for m in finditer(regexp, s):
        right, next = m.span()
        if right != 0:
            yield left, right
        left = next

def spans_to_relative(spans):
    prev = 0
    for left, right in spans:
        yield left - prev, right - left
        prev = right
