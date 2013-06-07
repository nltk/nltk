# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures

## Test bigram counters with discontinuous bigrams and repeated words

_EPSILON = 1e-8


def close_enough(x, y):
    """Verify that two sequences of n-gram association values are within
       _EPSILON of each other.
    """

    for (x1, y1) in zip(x, y):
        if x1[0] != y1[0] or abs(x1[1] - y1[1]) > _EPSILON:
            return False
    return True


def test_bigram2():

    sent = 'this this is is a a test test'.split()

    b = BigramCollocationFinder.from_words(sent)
    assert b.ngram_fd.items() == \
        [(('a', 'a'), 1), (('a', 'test'), 1), (('is', 'a'), 1), (('is', 'is'), 1), (('test', 'test'), 1), (('this', 'is'), 1), (('this', 'this'), 1)]
    assert b.word_fd.items() == \
        [('a', 2), ('is', 2), ('test', 2), ('this', 2)]
    assert len(sent) == sum(b.word_fd.values()) == sum(b.ngram_fd.values()) + 1
    assert close_enough(b.score_ngrams(BigramAssocMeasures.pmi), \
        [(('a', 'a'), 1.0), (('a', 'test'), 1.0), (('is', 'a'), 1.0), (('is', 'is'), 1.0), (('test', 'test'), 1.0), (('this', 'is'), 1.0), (('this', 'this'), 1.0)])


def test_bigram3():

    sent = 'this this is is a a test test'.split()

    b = BigramCollocationFinder.from_words(sent, window_size=3)
    assert b.ngram_fd.items() == \
        [(('a', 'test'), 3), (('is', 'a'), 3), (('this', 'is'), 3), (('a', 'a'), 1), (('is', 'is'), 1), (('test', 'test'), 1), (('this', 'this'), 1)]
    assert b.word_fd.items() == \
        [('a', 2), ('is', 2), ('test', 2), ('this', 2)]
    assert len(sent) == sum(b.word_fd.values()) == (sum(b.ngram_fd.values()) + 2 + 1) / 2.0
    assert close_enough(b.score_ngrams(BigramAssocMeasures.pmi),
        [(('a', 'test'), 1.584962500721156), (('is', 'a'), 1.584962500721156), (('this', 'is'), 1.584962500721156), (('a', 'a'), 0.0), (('is', 'is'), 0.0), (('test', 'test'), 0.0), (('this', 'this'), 0.0)])


def test_bigram5():

    sent = 'this this is is a a test test'.split()

    b = BigramCollocationFinder.from_words(sent, window_size=5)
    assert b.ngram_fd.items() == \
        [(('a', 'test'), 4), (('is', 'a'), 4), (('this', 'is'), 4), (('is', 'test'), 3), (('this', 'a'), 3), (('a', 'a'), 1), (('is', 'is'), 1), (('test', 'test'), 1), (('this', 'this'), 1)]
    assert b.word_fd.items() == \
        [('a', 2), ('is', 2), ('test', 2), ('this', 2)]
    assert len(sent) == sum(b.word_fd.values()) == (sum(b.ngram_fd.values()) + 4 + 3 + 2 + 1) / 4.0
    assert close_enough(b.score_ngrams(BigramAssocMeasures.pmi),
        [(('a', 'test'), 1.0), (('is', 'a'), 1.0), (('this', 'is'), 1.0), (('is', 'test'), 0.5849625007211562), (('this', 'a'), 0.5849625007211562), (('a', 'a'), -1.0), (('is', 'is'), -1.0), (('test', 'test'), -1.0), (('this', 'this'), -1.0)])
