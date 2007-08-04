# Natural Language Toolkit: Tagger Utilities
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import string

def tag2tuple(s, sep='/'):
    loc = s.rfind(sep)
    if loc >= 0:
        return (s[:loc], s[loc+1:].upper())
    else:
        return (s, None)

def untag(tagged_sentence):
    return (w for (w, t) in tagged_sentence)

def string2tags(s, sep='/'):
    return [tag2tuple(t, sep) for t in s.split()]

def tags2string(t, sep='/'):
    return string.join(token + sep + str(tag) for (token, tag) in t)

def string2words(s, sep='/'):
    return [tag2tuple(t, sep)[0] for t in s.split()]


from nltk import evaluate
def accuracy(tagger, gold):
    """
    Score the accuracy of the tagger against the gold standard.
    Strip the tags from the gold standard text, retag it using
    the tagger, then compute the accuracy score.

    @type tagger: C{TagI}
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


