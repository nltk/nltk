# Natural Language Toolkit: Tagger Utilities
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re

from nltk.metrics import accuracy as _accuracy

def str2tuple(s, sep='/'):
    """
    Given the string representation of a tagged token, return the
    corresponding tuple representation.  The rightmost occurrence of
    C{sep} in C{s} will be used to divide C{s} into a word string and
    a tag string.  If C{sep} does not occur in C{s}, return
    C{(s, None)}.

    @type s: C{str}
    @param s: The string representaiton of a tagged token.
    @type sep: C{str}
    @param sep: The separator string used to separate word strings
        from tags.
    """
    loc = s.rfind(sep)
    if loc >= 0:
        return (s[:loc], s[loc+len(sep):].upper())
    else:
        return (s, None)

def tuple2str(tagged_token, sep='/'):
    """
    Given the tuple representation of a tagged token, return the
    corresponding string representation.  This representation is
    formed by concatenating the token's word string, followed by the
    separator, followed by the token's tag.  (If the tag is None,
    then just return the bare word string.)
    
    @type tagged_token: C{(str, str)}
    @param tagged_token: The tuple representation of a tagged token.
    @type sep: C{str}
    @param sep: The separator string used to separate word strings
        from tags.
    """
    word, tag = tagged_token
    if tag is None:
        return word
    else:
        assert sep not in tag, 'tag may not contain sep!'
        return '%s%s%s' % (word, sep, tag)

def untag(tagged_sentence):
    """
    Given a tagged sentence, return an untagged version of that
    sentence.  I.e., return a list containing the first element
    of each tuple in C{tagged_sentence}.

    >>> untag([('John', 'NNP'), ('saw', 'VBD'), ('Mary', 'NNP')]
    ['John', 'saw', 'mary']
    """
    return [w for (w, t) in tagged_sentence]

