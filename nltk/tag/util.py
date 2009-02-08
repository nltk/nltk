# Natural Language Toolkit: Tagger Utilities
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re

from nltk.internals import deprecated
from nltk.metrics import accuracy as _accuracy

def str2tuple(s, sep='/'):
    """
    Given the string representation of a tagged token, return the
    corresponding tuple representation.  The rightmost occurence of
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
        return (s[:loc], s[loc+1:].upper())
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

@deprecated("use tagger.evaluate(gold)")
def accuracy(tagger, gold):
    return tagger.evaluate(gold)


######################################################################
#{ Deprecated
######################################################################
@deprecated("Use nltk.tag.str2tuple(s, sep) instead.")
def tag2tuple(s, sep='/'):
    return str2tuple(s, sep)

@deprecated("Use [nltk.tag.str2tuple(t, sep) for t in s.split()] instead.")
def string2tags(s, sep='/'):
    return [str2tuple(t, sep) for t in s.split()]

@deprecated("Use ' '.join(nltk.tag.tuple2str(w, sep) for w in t) instead.")
def tags2string(t, sep='/'):
    return ' '.join(tuple2str(w, sep) for w in t)

@deprecated("Use [nltk.tag.str2tuple(t, sep)[0] for t in s.split()] instead.")
def string2words(s, sep='/'):
    return [str2tuple(t, sep)[0] for t in s.split()]


