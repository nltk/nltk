# Natural Language Toolkit: N-Gram Taggers
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
from nltk.probability import FreqDist, ConditionalFreqDist
from nltk_lite.tag import *

##############################################################
# N-GRAM TAGGERS: these make use of history
##############################################################

class Queue:
    def __init__(self, length):
        self._length = length
        self.clear()
    def clear(self):
        self._queue = (None,) * self._length
    def enqueue(self, item):
        self._queue = (item,) + self._queue[:self._length-1]
    def set(self, items):
        if len(items) >= self._length:
            # restrict to required length
            self._queue = items[self._length:]
        else:
            # pad to required length
            self._queue = items + (None,) * (self._length - 1 - len(items))
    def get(self):
        return self._queue

class Ngram(SequentialBackoff):
    """
    An I{n}-gram stochastic tagger.  Before an C{tagger.Ngram}
    can be used, it should be trained on a tagged corpus.  Using this
    training data, it will construct a frequency distribution
    describing the frequencies with each word is tagged in different
    contexts.  The context considered consists of the word to be
    tagged and the I{n-1} previous words' tags.  Once the tagger has been
    trained, it uses this frequency distribution to tag words by
    assigning each word the tag with the maximum frequency given its
    context.  If the C{tagger.Ngram} encounters a word in a context
    for which it has no data, it will assign it the tag C{None}.
    """
    def __init__(self, n, cutoff=1, backoff=None):
        """
        Construct an I{n}-gram stochastic tagger.  The tagger must be trained
        using the L{train()} method before being used to tag data.
        
        @param n: The order of the new C{tagger.Ngram}.
        @type n: int
        @type cutoff: C{int}
        @param cutoff: A count-cutoff for the tagger's frequency
            distribution.  If the tagger saw fewer than
            C{cutoff} examples of a given context in training,
            then it will return a tag of C{None} for that context.
        """
        if n < 2: raise ValueError('n must be greater than 1')
        self._model = {}
        self._n = n
        self._cutoff = cutoff
        self._history = Queue(n-1)
        self._backoff = backoff

    def train(self, tagged_corpus, verbose=False):
        """
        Train this C{tagger.Ngram} using the given training data.
        
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
            self._history.clear()
            for (token, tag) in sentence:
                token_count += 1
                history = self._history.get()
                backoff_tag = self._backoff_tag_one(token, history)
                if tag != backoff_tag:
                    hit_count += 1
                    fd[(history, token)].inc(tag)
                self._history.enqueue(tag)
        for context in fd.conditions():
            best_tag = fd[context].max()
            if fd[context].count(best_tag) > self._cutoff:
                self._model[context] = best_tag
        # generate stats
        if verbose:
            size = len(self._model)
            backoff = 100 - (hit_count * 100.0)/ token_count
            pruning = 100 - (size * 100.0) / len(fd.conditions())
            print "[Trained %d-gram tagger:" % self._n,
            print "size=%d, backoff=%.2f%%, pruning=%.2f%%]" % (
                size, backoff, pruning)

    def tag_one(self, token, history=None):
        if self.size() == 0:
            raise ValueError, 'Tagger is not trained'
        if history:
            self._history.set(history) # NB this may truncate history
        history = self._history.get()
        context = (history, token)

        if self._model.has_key(context):
            return self._model[context]
        if self._backoff:
            return self._backoff.tag_one(token, history)
        return None

    def size(self):
        return len(self._model)

    def __repr__(self):
        return '<%d-gram Tagger: size=%d, cutoff=%d>' % (
            self._n, self.size(), self._cutoff)

class Bigram(Ngram):
    def __init__(self, cutoff=1, backoff=None):
        Ngram.__init__(self, 2, cutoff, backoff)

class Trigram(Ngram):
    def __init__(self, cutoff=1, backoff=None):
        Ngram.__init__(self, 3, cutoff, backoff)


###
#
#    def print_usage_stats(self):
#        total = self._total_count
#        print '  %20s | %s' % ('Tagger', 'Words Tagged')
#        print '  '+'-'*21+'|'+'-'*17
#        for tagger in self._taggers:
#            count = self._tagger_count[tagger]
#            print '  %20s |    %4.1f%%' % (tagger, 100.0*count/total)
#
#    def __repr__(self):
#        return '<BackoffTagger: %s>' % self._taggers
###
    
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

#    t1a = Affix(length=-3, minlength=5, backoff=t0)
#    t1b = Unigram(cutoff=2, backoff=t1a)
    t1 = Unigram(cutoff=1, backoff=t0)
    t2 = Bigram(cutoff=1, backoff=t1)
    t3 = Trigram(backoff=t2)

    t1.train(brown.tagged('a'), verbose=True)
    t2.train(brown.tagged('a'), verbose=True)
    t3.train(brown.tagged('a'), verbose=True)

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

    print '  Bigram tagger:       ',
    sys.stdout.flush()
    _demo_tagger(t2, list(brown.tagged('b'))[:1000])

    print '  Trigram tagger:       ',
    sys.stdout.flush()
    _demo_tagger(t3, list(brown.tagged('b'))[:1000])

#        print '\nUsage statistics for the trigram tagger:\n'
#        trigram.print_usage_stats()
#        print '='*75

if __name__ == '__main__':
    demo()

