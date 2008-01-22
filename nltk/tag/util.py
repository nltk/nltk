# Natural Language Toolkit: Tagger Utilities
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.internals import deprecated

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

from nltk import evaluate
def accuracy(tagger, gold):
    """
    Score the accuracy of the tagger against the gold standard.
    Strip the tags from the gold standard text, retag it using
    the tagger, then compute the accuracy score.

    @type tagger: C{TaggerI}
    @param tagger: The tagger being evaluated.
    @type gold: C{list} of C{Token}
    @param gold: The list of tagged tokens to score the tagger on.
    @rtype: C{float}
    """

    gold_tokens = []
    test_tokens = []
    for sent in gold:
        sent = list(sent)
        gold_tokens += sent
        test_tokens += list(tagger.tag(untag(sent)))

    return evaluate.accuracy(gold_tokens, test_tokens)

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


