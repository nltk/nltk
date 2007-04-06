# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for tagging each token of a document with
supplementary information, such as its part of speech or its WordNet
synset tag.  This task, which is known as X{tagging}, is defined by
the L{TagI} interface.
"""

import yaml

class TagI(yaml.YAMLObject):
    """
    A processing interface for assigning a tag to each token in a list.
    Tags are case sensitive strings that identify some property of each
    token, such as its part of speech or its sense.
    """
    def tag(self, tokens):
        """
        Assign a tag to each token in C{tokens}, and yield a tagged token
        of the form (token, tag)
        """
        raise NotImplementedError()

class SequentialBackoff(TagI):
    """
    A tagger that tags words sequentially, left to right.
    """
    def tag(self, tokens, verbose=False):
        for token in tokens:
            if isinstance(token, list):
                yield list(self.tag(token, verbose))
            else:
                tag = self.tag_one(token)
                if tag == None and self._backoff:
                    tag = self._backoff.tag_one(token)
                if self._history:
                    del self._history[0]
                    self._history.append(tag)
                yield (token, tag)

    def tag_sents(self, sents, verbose=False):
        for sent in sents:
            yield list(self.tag(sent, verbose))

    def _backoff_tag_one(self, token, history=None):
        if self._backoff:
            return self._backoff.tag_one(token, history)
        else:
            return None
    
class Default(SequentialBackoff):
    """
    A tagger that assigns the same tag to every token.
    """
    yaml_tag = '!tag.Default'
    def __init__(self, tag):
        """
        Construct a new default tagger.

        @type tag: C{string}
        @param tag: The tag that should be assigned to every token.
        """
        self._tag = tag
        self._backoff = None # cannot have a backoff tagger!
        self._history = None
        
    def tag_one(self, token, history=None):
        return self._tag  # ignore token and history

    def __repr__(self):
        return '<DefaultTagger: tag=%s>' % self._tag


##################################################################
# UTILITY FUNCTIONS
##################################################################

from nltk_lite import tokenize

def tag2tuple(s, sep='/'):
    loc = s.rfind(sep)
    if loc >= 0:
        return (s[:loc], s[loc+1:])
    else:
        return (s, None)

def untag(tagged_sentence):
    return (w for (w, t) in tagged_sentence)

def string2tags(s, sep='/'):
    return [tag2tuple(t, sep) for t in tokenize.whitespace(s)]

def tags2string(t, sep='/'):
    return " ".join(token + sep + str(tag) for (token, tag) in t)

def string2words(s, sep='/'):
    return [tag2tuple(t, sep)[0] for t in tokenize.whitespace(s)]

##################################################################
# EVALUATION
##################################################################

from nltk_lite import evaluate
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

#    print 'GOLD:', gold_tokens[:50]
#    print 'TEST:', test_tokens[:50]
    return evaluate.accuracy(gold_tokens, test_tokens)

#############################################################

from unigram import *
from ngram import *
from brill import *
