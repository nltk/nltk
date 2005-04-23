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
    def tag(self, token):
        """
        Assign a tag to each subtoken in C{token['SUBTOKENS']}, and
        write those tags to the subtokens' C{tag} properties.
        """
        raise NotImplementedError()


class DefaultTagger(TaggerI):
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
        
    def tag(self, tokens):
        for t in tokens:
            yield (t, self._tag)
    
    def __repr__(self):
        return '<DefaultTagger: %s>' % self._tag

class RegexpTagger(TaggerI):
    """
    A tagger that assigns tags to words based on regular expressions.
    """
    def __init__(self, regexps):
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

    def tag(self, tokens):
        for t in tokens:
            for regexp, tag in self._regexps:
                if re.match(regexp, t):
                    yield (t, tag)
            yield (t, None)
                                      
    def __repr__(self):
        return '<RegexprTagger: %d regexps>' % len(self._regexps)

class UnigramTagger(TaggerI):
    """
    A unigram stochastic tagger.  Before a C{UnigramTagger} can be
    used, it should be trained on a tagged corpus.  Using this
    training data, it will find the most likely tag for each word
    type.  It will then use this information to assign the most
    frequent tag to each word.  If the C{UnigramTagger} encounters a
    word which it has no data, it will assign it the
    tag C{None}.
    """
    def __init__(self):
        """
        Construct a new unigram stochastic tagger.  The new tagger
        should be trained, using the L{train()} method, before it is
        used to tag data.
        """
        self._freqdist = ConditionalFreqDist()

    def train(self, tagged_tokens):
        """
        Train this C{UnigramTagger} using the given training data.  If
        this method is called multiple times, then the training data
        will be combined.
        
        @param tagged_tokens: A tagged corpus.  Each token in
            C{tagged_tokens} should be a tuple consisting of
            C{text} and a C{tag}.
        @type tagged_tokens: C{tuple} or C{iter(tuple)}
        """

        # Record each text/tag pair in the frequency distribution.
        for (word, tag) in tagged_tokens:
            self._freqdist[word].inc(tag)

    def tag(self, tokens):
        # Find the most likely tag for the tokens.
        for t in tokens:
            yield (t, self._freqdist[t].max())

    def __repr__(self):
        return '<Unigram Tagger>'

class Queue:
    def __init__(self, length):
        self._length = length
        self._queue = ":" * (self._length - 1)
    def enqueue(self, item):
        self._queue = item + ":" + self._queue
        i = self._queue.rfind(":")
        self._queue = self._queue[:i]
    def queue(self):
        return self._queue

class NGramTagger(TaggerI):
    """
    An I{n}-gram stochastic tagger.  Before an C{NGramTagger}
    can be used, it should be trained on a tagged corpus.  Using this
    training data, it will construct a frequency distribution
    describing the frequencies with each word is tagged in different
    contexts.  The context considered consists of the word to be
    tagged and the I{n} previous words' tags.  Once the tagger has been
    trained, it uses this frequency distribution to tag words by
    assigning each word the tag with the maximum frequency given its
    context.  If the C{NGramTagger} encounters a word in a context
    for which it has no data, it will assign it the tag C{None}.
    """
    def __init__(self, n, cutoff=0):
        """
        Construct a new I{n}-gram stochastic tagger.  The new
        tagger should be trained, using the L{train()} method, before
        it is used to tag data.
        
        @param n: The order of the new C{NGramTagger}.
        @type n: int
        @type cutoff: C{int}
        @param cutoff: A count-cutoff for the tagger's frequency
            distribution.  If the tagger saw fewer than
            C{cutoff} examples of a given context in training,
            then it will return a tag of C{None} for that context.
        """
        if n < 0: raise ValueError('n must be non-negative')
        self._freqdist = ConditionalFreqDist()
        self._n = n
        self._cutoff = cutoff
        self._recent_tags = Queue(n-1)

    def train(self, tagged_tokens):
        """
        Train this C{NGramTagger} using the given training data.
        If this method is called multiple times, then the training
        data will be combined.
        
        @param tagged_tokens: A tagged corpus.  Each token in
            C{tagged_tokens} should be a tuple consisting of
            C{text} and a C{tag}.
        @type tagged_tokens: C{tuple} or C{iter(tuple)}
        """
        for (word, tag) in tagged_tokens:
            context = (self._recent_tags, word)
            self._freqdist[context].inc(tag)
            self._recent_tags.enqueue(tag)

    def tag(self, words):
        # Construct the context from the current subtoken's text and
        # the adjacent tokens' tags.
                        
        for word in words:
            context = (self._recent_tags, word)
            tag = self._freqdist[context].max()

            # If we're sufficiently confident in this tag, then return it.
            # Otherwise, return None.
            if self._freqdist[context].count(tag) >= self._cutoff:
                yield (word, tag)
            else:
                yield (word, None)

    def __repr__(self):
        n = repr(self._n)
        return '<%s-gram Tagger>' % n

# class BackoffTagger(TaggerI):
#     """
#     A C{Tagger} that tags tokens using a basic backoff model.  Each
#     C{BackoffTagger} is paramaterised by an ordered list sub-taggers.
#     In order to assign a tag to a token, each of these sub-taggers is
#     consulted in order.  If a sub-tagger is unable to determine a tag
#     for the given token, it should use assign the special tag C{None}.
#     Each token is assigned the first non-C{None} tag returned by a
#     tagger.
#     """
#     def __init__(self, taggers):
#         """
#         Construct a new C{BackoffTagger}, from the given
#         list of taggers.
        
#         @param taggers: The list of taggers used by this
#                C{BackoffTagger}.  These taggers will be
#                consulted in the order in which they appear in the list.
#         @type taggers: list of SequentialTagger
#         """
#         self._taggers = taggers

#         # Keep a record of how often each tagger was used
#         self._tagger_count = {}
#         for tagger in taggers:
#             self._tagger_count[tagger] = 0
#         self._total_count = 0

# ##
# ## PROBLEM: how do we manage the global history?
# ## must happen outside the queue constructed by each tagger
# ## => sequential tagger must be a kind of tagger that takes
# ##   history as an argument; this is how we will distinguish
# ##   its signature from other taggers?
# ##
#     def tag(self, tokens):
#         self._total_count += 1
#         for token in tokens:
#             for tagger in self._taggers:
#                 tag = tagger.tag(token)
#                 if tag is not None:
#                     self._tagger_count[tagger] += 1
#                     return tag

#         # Default to None if all taggers return None.
#         return None

#     def print_usage_stats(self):
#         total = self._total_count
#         print '  %20s | %s' % ('Tagger', 'Words Tagged')
#         print '  '+'-'*21+'|'+'-'*17
#         for tagger in self._taggers:
#             count = self._tagger_count[tagger]
#             print '  %20s |    %4.1f%%' % (tagger, 100.0*count/total)

#     def __repr__(self):
#         return '<BackoffTagger: %s>' % self._taggers
    
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
    print 'GOLD:', gold[:20]
    print 'TEST:', test[:20]
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
    default_tagger = DefaultTagger('nn')

    t1 = UnigramTagger()
    t2 = NGramTagger(2)
#    t3 = NGramTagger(3)

    t1.train(brown('a'))
    t2.train(brown('a'))
#    t3.train(brown('a'))

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
    _demo_tagger(default_tagger, brown('a'))

    print '  Unigram tagger:      ',
    sys.stdout.flush()
    _demo_tagger(t1, brown('a'))
#    _demo_tagger(BackoffTagger([t0, default_tagger]), brown('a'))

    print '  Bigram tagger:       ',
    sys.stdout.flush()
    _demo_tagger(t2, brown('a'))

#    _demo_tagger(BackoffTagger([t1, t0, default_tagger]), brown('a'))

#
#        print '  Trigram tagger:      ',
#        sys.stdout.flush()
#        trigram = BackoffTagger([t3, t2, t1, default_tagger])
#        _demo_tagger(test_tokens, trigram)

#        print '\nUsage statistics for the trigram tagger:\n'
#        trigram.print_usage_stats()
#        print '='*75

if __name__ == '__main__':
    # Standard boilerpate.  (See note in <http://?>)
    #from nltk.tagger import *
    from corpus import set_basedir
    set_basedir('/data/nltk/data/')   # location for modified corpus
    demo()

