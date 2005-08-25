# Natural Language Toolkit: Unigram Taggers
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for tagging each token of a document with
supplementary information, such as its part of speech or its WordNet
synset tag.  This task, which is known as X{tagging}, is defined by
the L{TaggerI} interface.
"""

import types, re
from nltk_lite.probability import FreqDist, ConditionalFreqDist

##############################################################
# UNIGRAM TAGGERS: only use information about the current word
##############################################################

from nltk_lite.tag import *

class Unigram(SequentialBackoff):
    """
    A unigram stochastic tagger.  Before C{tag.Unigram} can be
    used, it should be trained on a tagged corpus.  Using this
    training data, it will find the most likely tag for each word
    type.  It will then use this information to assign the most
    frequent tag to each word.  If C{tag.Unigram} encounters a
    word which it has no data, it will assign it the
    tag C{None}.
    """
    def __init__(self, cutoff=1, backoff=None):
        """
        Construct a new unigram stochastic tagger.  The new tagger
        should be trained, using the L{train()} method, before it is
        used to tag data.
        """
        self._model = {}
        self._cutoff = cutoff
        self._backoff = backoff
        self._history = None
        
    def train(self, tagged_corpus, verbose=False):
        """
        Train C{tag.Unigram} using the given training data.
        
        @param tagged_corpus: A tagged corpus.  Each item should be
            a C{list} of tagged tokens, where each consists of
            C{text} and a C{tag}.
        @type tagged_corpus: C{list} or C{iter(list)}
        """

        if self.size() != 0:
            raise ValueError, 'Tagger is already trained'
        token_count = hit_count = 0
        fd = ConditionalFreqDist()
        for sentence in tagged_corpus:
            for (token, tag) in sentence:
                token_count += 1
                backoff_tag = self._backoff_tag_one(token)
                if tag != backoff_tag:
                    hit_count += 1
                    fd[token].inc(tag)
        for token in fd.conditions():
            best_tag = fd[token].max()
            if fd[token].count(best_tag) > self._cutoff:
                self._model[token] = best_tag
        # generate stats
        if verbose:
            size = len(self._model)
            backoff = 100 - (hit_count * 100.0)/ token_count
            pruning = 100 - (size * 100.0) / len(fd.conditions())
            print "[Trained Unigram tagger:",
            print "size=%d, backoff=%.2f%%, pruning=%.2f%%]" % (
                size, backoff, pruning)

    def tag_one(self, token, history=None):
        if self.size() == 0:
            raise ValueError, 'Tagger is not trained'
        if self._model.has_key(token):
            return self._model[token]
        if self._backoff:
            return self._backoff.tag_one(token, history)
        return None

    def size(self):
        return len(self._model)

    def __repr__(self):
        return '<Unigram Tagger: size=%d, cutoff=%d>' % (
            self.size(), self._cutoff)


# Affix tagger, based on code by Tiago Tresoldi <tresoldi@users.sf.net>
class Affix(SequentialBackoff):
    """
    A unigram tagger that assign tags to tokens based on leading or
    trailing substrings (it is important to note that the substrings
    are not necessarily "true" morphological affixes).  Before
    C{tag.Affix} can be used, it should be trained on a tagged
    corpus. Using this training data, it will find the most likely tag
    for each word type. It will then use this information to assign
    the most frequent tag to each word. If the C{tag.Affix}
    encounters a prefix or suffix in a word for which it has no data,
    it will assign the tag C{None}.
    """
    def __init__ (self, length, minlength, cutoff=1, backoff=None):
        """
        Construct a new affix stochastic tagger. The new tagger should be
        trained, using the L{train()} method, before it is used to tag
        data.
        
        @type length: C{number}
        @param length: The length of the affix to be considered during 
            training and tagging (negative for suffixes)
        @type minlength: C{number}
        @param minlength: The minimum length for a word to be considered
            during training and tagging. It must be longer that C{length}.
        """
#        SequentialBackoff.__init__(self)
        self._model = {}
        
        assert minlength > 0
        
        self._length = length
        self._minlength = minlength
        self._cutoff = cutoff
        self._backoff = backoff
        self._history = None
        
    def _get_affix(self, token):
        if self._length > 0:
            return token[:self._length]
        else:
            return token[self._length:]

    def train(self, tagged_corpus, verbose=False):
        """
        Train C{tag.Affix} using the given training data. If this
        method is called multiple times, then the training data will be
        combined.
        
        @param tagged_corpus: A tagged corpus.  Each item should be
            a C{list} of tagged tokens, where each consists of
            C{text} and a C{tag}.
        @type tagged_corpus: C{list} or C{iter(list)}
        """

        if self.size() != 0:
            raise ValueError, 'Tagger is already trained'
        token_count = hit_count = 0
        fd = ConditionalFreqDist()
        
        for sentence in tagged_corpus:
            for (token, tag) in sentence:
                token_count += 1
                # If token is long enough
                if len(token) >= self._minlength:
                    backoff_tag = self._backoff_tag_one(token)
                    if tag != backoff_tag:
                        # get the affix and record it
                        affix = self._get_affix(token)
                        hit_count += 1
                        fd[affix].inc(tag)
        for affix in fd.conditions():
            best_tag = fd[affix].max()
            if fd[affix].count(best_tag) > self._cutoff:
                self._model[affix] = best_tag
        # generate stats
        if verbose:
            size = len(self._model)
            backoff = 100 - (hit_count * 100.0)/ token_count
            pruning = 100 - (size * 100.0) / len(fd.conditions())
            print "[Trained Affix tagger:",
            print "size=%d, backoff=%.2f%%, pruning=%.2f%%]" % (
                size, backoff, pruning)

    def tag_one(self, token, history=None):
        if self.size() == 0:
            raise ValueError, 'Tagger is not trained'
        affix = self._get_affix(token)
        if len(token) >= self._minlength and self._model.has_key(affix):
            return self._model[affix]
        if self._backoff:
            return self._backoff.tag_one(token, history)
        return None

    def size(self):
        return len(self._model)

    def __repr__(self):
        return '<Affix Tagger: size=%d, cutoff=%d>' % (
            self.size(), self._cutoff)


class Regexp(SequentialBackoff):
    """
    A tagger that assigns tags to words based on regular expressions.
    """
    def __init__(self, regexps, backoff=None):
        """
        Construct a new regexp tagger.

        @type regexps: C{list} of C{(string,string)}
        @param regexps: A list of C{(regexp,tag)} pairs, each of
            which indicates that a word matching C{regexp} should
            be tagged with C{tag}.  The pairs will be evalutated in
            order.  If none of the regexps match a word, then it is
            assigned the tag C{None}.
        """
        self._regexps = regexps
        self._backoff = backoff
        self._history = None

    def tag_one(self, token, history=None):
        for regexp, tag in self._regexps:
            if re.match(regexp, token): # ignore history
                return tag
        if self._backoff:
            return self._backoff.tag_one(token, history)
        return None

    def __repr__(self):
        return '<Regexp Tagger: size=%d>' % len(self._regexps)

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def _demo_tagger(tagger, gold):
    from nltk_lite.tag import accuracy
    acc = accuracy(tagger, gold)
    print 'Accuracy = %4.1f%%' % (100.0 * acc)

def demo():
    """
    A simple demonstration function for the C{Tagger} classes.  It
    constructs a backoff tagger using a trigram tagger, bigram tagger
    unigram tagger and a default tagger.  It trains and tests the
    tagger using the Brown corpus.
    """
    from nltk_lite.corpora import brown
    import sys

    print 'Training taggers.'

    # Create a default tagger
    t0 = Default('nn')

    t1 = Unigram(cutoff=1, backoff=t0)
    t1.train(brown.tagged('a'), verbose=True)

    t2 = Affix(-3, 5, cutoff=2, backoff=t0)
    t2.train(brown.tagged('a'), verbose=True)

    t3 = Regexp([(r'.*ed', 'vbd')], backoff=t0)  # no training

    # Tokenize the testing files
    test_tokens = []
    num_words = 0

    # Run the taggers.  For t0, t1, and t2, back-off to DefaultTagger.
    # This is especially important for t1 and t2, which count on
    # having known tags as contexts; if they get a context containing
    # None, then they will generate an output of None, and so all
    # words will get tagged a None.

    print '='*75
    print 'Running the taggers on test data...'
    print '  Default (nn) tagger: ',
    sys.stdout.flush()
    _demo_tagger(t0, brown.tagged('b'))

    print '  Unigram tagger:      ',
    sys.stdout.flush()
    _demo_tagger(t1, list(brown.tagged('b'))[:1000])

    print '  Affix tagger:      ',
    sys.stdout.flush()
    _demo_tagger(t2, list(brown.tagged('b'))[:1000])

    print '  Regexp tagger:      ',
    sys.stdout.flush()
    _demo_tagger(t3, list(brown.tagged('b'))[:1000])

if __name__ == '__main__':
    demo()

