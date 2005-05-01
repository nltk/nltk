# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes and interfaces for tagging each token of a document with
supplementary information, such as its part of speech or its WordNet
synset tag.  This task, which is known as X{tagging}, is defined by
the L{TaggerI} interface.
"""

import types, re
from nltk.probability import FreqDist, ConditionalFreqDist

class TaggerI:
    """
    A processing interface for assigning a tag to each subtoken in an
    ordered list of subtokens.  Tags are case sensitive strings that
    identify some aspect each subtoken, such as its part of speech or
    its word sense.
    """
    def tag(self, tokens):
        """
        Assign a tag to each token in C{tokens}, and yield a tagged token
        of the form (token, tag)
        """
        raise NotImplementedError()

class SequentialBackoffTagger(TaggerI):
    """
    A tagger that tags words sequentially, left to right.
    """
    def tag(self, tokens, verbose=False):
        for token in tokens:
            tag = self.tag_one(token)
            if tag == None and self._backoff:
                tag = self._backoff.tag_one(token)
            if self._history:
                self._history.enqueue(tag)
            yield (token, tag)

    def _backoff_tag_one(self, token, history=None):
        if self._backoff:
            return self._backoff.tag_one(token, history)
        else:
            return None
    
### Taggers that ignore history

class DefaultTagger(SequentialBackoffTagger):
    """
    A tagger that assigns the same tag to every token.
    """
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

class RegexpTagger(SequentialBackoffTagger):
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
        return None

    def __repr__(self):
        return '<RegexpTagger: size=%d>' % len(self._regexps)

class UnigramTagger(SequentialBackoffTagger):
    """
    A unigram stochastic tagger.  Before a C{UnigramTagger} can be
    used, it should be trained on a tagged corpus.  Using this
    training data, it will find the most likely tag for each word
    type.  It will then use this information to assign the most
    frequent tag to each word.  If the C{UnigramTagger} encounters a
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
        
    def train(self, tagged_tokens, verbose=False):
        """
        Train this C{UnigramTagger} using the given training data.
        
        @param tagged_tokens: A tagged corpus.  Each token in
            C{tagged_tokens} should be a tuple consisting of
            C{text} and a C{tag}.
        @type tagged_tokens: C{tuple} or C{iter(tuple)}
        """

        if self.size() != 0:
            raise ValueError, 'Tagger is already trained'
        token_count = hit_count = 0
        fd = ConditionalFreqDist()
        for (token, tag) in tagged_tokens:
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


### Taggers that use history

class Queue:
    def __init__(self, length):
        self._length = length
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

class NGramTagger(SequentialBackoffTagger):
    """
    An I{n}-gram stochastic tagger.  Before an C{NGramTagger}
    can be used, it should be trained on a tagged corpus.  Using this
    training data, it will construct a frequency distribution
    describing the frequencies with each word is tagged in different
    contexts.  The context considered consists of the word to be
    tagged and the I{n-1} previous words' tags.  Once the tagger has been
    trained, it uses this frequency distribution to tag words by
    assigning each word the tag with the maximum frequency given its
    context.  If the C{NGramTagger} encounters a word in a context
    for which it has no data, it will assign it the tag C{None}.
    """
    def __init__(self, n, cutoff=1, backoff=None):
        """
        Construct an I{n}-gram stochastic tagger.  The tagger must be trained
        using the L{train()} method before being used to tag data.
        
        @param n: The order of the new C{NGramTagger}.
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

    def train(self, tagged_tokens, verbose=False):
        """
        Train this C{NGramTagger} using the given training data.
        
        @param tagged_tokens: Tagged training data.  Each token in
            C{tagged_tokens} should be a tuple consisting of
            C{text} and a C{tag}.
        @type tagged_tokens: C{tuple} or C{iter(tuple)}
        """

        if self.size() != 0:
            raise ValueError, 'Tagger is already trained'
        token_count = hit_count = 0
        fd = ConditionalFreqDist()
        for (token, tag) in tagged_tokens:
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

class BigramTagger(NGramTagger):
    def __init__(self, cutoff=1, backoff=None):
        NGramTagger.__init__(self, 2, cutoff, backoff)

class TrigramTagger(NGramTagger):
    def __init__(self, cutoff=1, backoff=None):
        NGramTagger.__init__(self, 3, cutoff, backoff)

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
    
from nltk.eval import accuracy
def tagger_accuracy(tagger, gold):
    """
    Score the accuracy of the tagger against the gold standard.
    Strip the tags from the gold standard text, retag it using
    the tagger, then compute the accuracy score.

    @type tagger: C{Tagger}
    @param tagger: The tagger being evaluated.
    @type gold: C{list} of C{Token}
    @param gold: The list of tagged tokens to score the tagger on.
    @rtype: C{float}
    """

    gold = list(gold)
    test = list(tagger.tag(word for (word, tag) in gold))
    print 'GOLD:', gold[:50]
    print 'TEST:', test[:50]
    return accuracy(gold, test)

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def _demo_tagger(tagger, gold):
    acc = tagger_accuracy(tagger, gold)
    print 'Accuracy = %4.1f%%' % (100.0 * acc)

def demo(num_files=20):
    """
    A simple demonstration function for the C{Tagger} classes.  It
    constructs a C{BackoffTagger} using a 2nd order C{NthOrderTagger},
    a 1st order C{NthOrderTagger}, a 0th order C{NthOrderTagger}, and
    an C{DefaultTagger}.  It trains and tests the tagger using the
    brown corpus.

    @type num_files: C{int}
    @param num_files: The number of files that should be used for
        training and for testing.  Two thirds of these files will be
        used for training.  All files are randomly selected
        (I{without} replacement) from the brown corpus.  If
        C{num_files>=500}, then all 500 files will be used.
    @rtype: None
    """
    from corpus import brown
    import sys, random
    num_files = max(min(num_files, 500), 3)

    print 'Training taggers.'

    # Create a default tagger
    t0 = DefaultTagger('nn'); print t0

    t1 = UnigramTagger(cutoff=2, backoff=t0)
    t2 = BigramTagger(cutoff=0, backoff=t1)
    t3 = TrigramTagger(backoff=t2)

    t1.train(brown('a'), verbose=True)
    t2.train(brown('a'), verbose=True)
    t3.train(brown('a'), verbose=True)

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
    _demo_tagger(t0, brown('b'))

    print '  Unigram tagger:      ',
    sys.stdout.flush()
    _demo_tagger(t1, list(brown('b'))[:1000])

    print '  Bigram tagger:       ',
    sys.stdout.flush()
    _demo_tagger(t2, list(brown('b'))[:1000])

    print '  Trigram tagger:       ',
    sys.stdout.flush()
    _demo_tagger(t3, list(brown('b'))[:1000])

#        print '\nUsage statistics for the trigram tagger:\n'
#        trigram.print_usage_stats()
#        print '='*75

if __name__ == '__main__':
    # Standard boilerpate.  (See note in <http://?>)
    #from nltk.tagger import *
    from corpus import set_basedir
#    set_basedir('/data/nltk/data/')   # location for modified corpus
    set_basedir('/home/sb/nltk/data/')   # location for modified corpus
    demo()

