# Natural Language Toolkit: Unigram Taggers
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

from nltk import FreqDist, ConditionalFreqDist

##############################################################
# UNIGRAM TAGGERS: only use information about the current word
##############################################################

from api import *
from util import *
import re

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
    yaml_tag = '!tag.Unigram'
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

        if isinstance(tagged_corpus, list) and isinstance(tagged_corpus[0], tuple):
            tagged_corpus = [tagged_corpus]

        for sentence in tagged_corpus:
            for (token, tag) in sentence:
                token_count += 1
                fd[token].inc(tag)
        for token in fd.conditions():
            best_tag = fd[token].max()
            backoff_tag = self._backoff_tag_one(token)
            hits = fd[token][best_tag]

            # is the tag we would assign different from the backoff tagger
            # and do we have sufficient evidence?
            if best_tag != backoff_tag and hits > self._cutoff:
                self._model[token] = best_tag
                hit_count += hits
            
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
        if token in self._model:
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
            if fd[affix][best_tag] > self._cutoff:
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
        if len(token) >= self._minlength and affix in self._model:
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
    yaml_tag = '!tag.Regexp'
    def __init__(self, regexps, backoff=None):
        """
        Construct a new regexp tagger.

        @type regexps: C{list} of C{(string,string)}
        @param regexps: A list of C{(regexp,tag)} pairs, each of
            which indicates that a word matching C{regexp} should
            be tagged with C{tag}.  The pairs will be evalutated in
            order.  If none of the regexps match a word, then the
            optional backoff tagger is invoked, else it is
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

class Lookup(SequentialBackoff):
    """
    A tagger that assigns tags to words based on a lookup table.
    """
    def __init__(self, table, backoff=None):
        """
        Construct a new lookup tagger.

        @type table: C{dict} from C{string} to C{string}
        @param table: A dictionary mapping words to tags,
            which indicates that a particular Cword should be assigned
            a given Ctag.  If none of the regexps match a word, then the
            optional backoff tagger is invoked, else it is
            assigned the tag C{None}.
        """
        self._table = table
        self._backoff = backoff
        self._history = None

    def tag_one(self, token, history=None):
        if token in self._table:
            return self._table[token]
        if self._backoff:
            return self._backoff.tag_one(token, history)
        return None

    def __repr__(self):
        return '<Lookup Tagger: size=%d>' % len(self._table)

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def _demo_tagger(tagger, gold):
    from nltk.tag import accuracy
    acc = accuracy(tagger, gold)
    print 'Accuracy = %4.1f%%' % (100.0 * acc)

def demo():
    """
    A simple demonstration function for the C{Tagger} classes.  It
    constructs a backoff tagger using a trigram tagger, bigram tagger
    unigram tagger and a default tagger.  It trains and tests the
    tagger using the Brown corpus.
    """
    from nltk.corpus import brown
    from nltk import tag
    import sys

    train_data = brown.tagged('a')
    test_data = brown.tagged('b')[:1000]

    print 'Training taggers.'

    # Create a default tagger
    t0 = tag.Default('nn')
    
    t1 = tag.Unigram(cutoff=1, backoff=t0)
    t1.train(train_data, verbose=True)

    t2 = tag.Affix(-3, 5, cutoff=2, backoff=t0)
    t2.train(train_data, verbose=True)

    t3 = tag.Regexp([(r'.*ed', 'vbd')], backoff=t0)  # no training

    t4 = tag.Lookup({'the': 'dt'}, backoff=t0)

    test_tokens = []
    num_words = 0

    print '='*75
    print 'Running the taggers on test data...'
    print '  Default (nn) tagger: ',
    sys.stdout.flush()
    _demo_tagger(t0, test_data)

    print '  Unigram tagger:      ',
    sys.stdout.flush()
    _demo_tagger(t1, test_data)

    print '  Affix tagger:        ',
    sys.stdout.flush()
    _demo_tagger(t2, test_data)

    print '  Regexp tagger:       ',
    sys.stdout.flush()
    _demo_tagger(t3, test_data)

    print '  Lookup tagger:       ',
    sys.stdout.flush()
    _demo_tagger(t4, test_data)

if __name__ == '__main__':
    demo()

