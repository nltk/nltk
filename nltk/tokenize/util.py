# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

from re import finditer

def string_span_tokenize(s, sep):
    """
    Identify the tokens in the string, as defined by the token
    delimiter, and generate (start, end) offsets.
    
    @param s: the string to be tokenized
    @type s: C{str}
    @param sep: the token separator
    @type sep: C{str}
    @rtype: C{iter} of C{tuple} of C{int}
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
    Identify the tokens in the string, as defined by the token
    delimiter regexp, and generate (start, end) offsets.
    
    @param s: the string to be tokenized
    @type s: C{str}
    @param regexp: the token separator regexp
    @type regexp: C{str}
    @rtype: C{iter} of C{tuple} of C{int}
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
    Convert absolute token spans to relative spans.
    
    @param spans: the (start, end) offsets of the tokens
    @type s: C{iter} of C{tuple} of C{int}
    @rtype: C{iter} of C{tuple} of C{int}
    """
    prev = 0
    for left, right in spans:
        yield left - prev, right - left
        prev = right
