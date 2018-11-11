# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest

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


class TestBigram(unittest.TestCase):
    def test_bigram2(self):
        sent = 'this this is is a a test test'.split()

        b = BigramCollocationFinder.from_words(sent)

        # python 2.6 does not have assertItemsEqual or assertListEqual
        self.assertEqual(
            sorted(b.ngram_fd.items()),
            sorted(
                [
                    (('a', 'a'), 1),
                    (('a', 'test'), 1),
                    (('is', 'a'), 1),
                    (('is', 'is'), 1),
                    (('test', 'test'), 1),
                    (('this', 'is'), 1),
                    (('this', 'this'), 1),
                ]
            ),
        )
        self.assertEqual(
            sorted(b.word_fd.items()),
            sorted([('a', 2), ('is', 2), ('test', 2), ('this', 2)]),
        )
        self.assertTrue(
            len(sent) == sum(b.word_fd.values()) == sum(b.ngram_fd.values()) + 1
        )
        self.assertTrue(
            close_enough(
                sorted(b.score_ngrams(BigramAssocMeasures.pmi)),
                sorted(
                    [
                        (('a', 'a'), 1.0),
                        (('a', 'test'), 1.0),
                        (('is', 'a'), 1.0),
                        (('is', 'is'), 1.0),
                        (('test', 'test'), 1.0),
                        (('this', 'is'), 1.0),
                        (('this', 'this'), 1.0),
                    ]
                ),
            )
        )

    def test_bigram3(self):
        sent = 'this this is is a a test test'.split()

        b = BigramCollocationFinder.from_words(sent, window_size=3)
        self.assertEqual(
            sorted(b.ngram_fd.items()),
            sorted(
                [
                    (('a', 'test'), 3),
                    (('is', 'a'), 3),
                    (('this', 'is'), 3),
                    (('a', 'a'), 1),
                    (('is', 'is'), 1),
                    (('test', 'test'), 1),
                    (('this', 'this'), 1),
                ]
            ),
        )
        self.assertEqual(
            sorted(b.word_fd.items()),
            sorted([('a', 2), ('is', 2), ('test', 2), ('this', 2)]),
        )
        self.assertTrue(
            len(sent)
            == sum(b.word_fd.values())
            == (sum(b.ngram_fd.values()) + 2 + 1) / 2.0
        )
        self.assertTrue(
            close_enough(
                sorted(b.score_ngrams(BigramAssocMeasures.pmi)),
                sorted(
                    [
                        (('a', 'test'), 1.584962500721156),
                        (('is', 'a'), 1.584962500721156),
                        (('this', 'is'), 1.584962500721156),
                        (('a', 'a'), 0.0),
                        (('is', 'is'), 0.0),
                        (('test', 'test'), 0.0),
                        (('this', 'this'), 0.0),
                    ]
                ),
            )
        )

    def test_bigram5(self):
        sent = 'this this is is a a test test'.split()

        b = BigramCollocationFinder.from_words(sent, window_size=5)
        self.assertEqual(
            sorted(b.ngram_fd.items()),
            sorted(
                [
                    (('a', 'test'), 4),
                    (('is', 'a'), 4),
                    (('this', 'is'), 4),
                    (('is', 'test'), 3),
                    (('this', 'a'), 3),
                    (('a', 'a'), 1),
                    (('is', 'is'), 1),
                    (('test', 'test'), 1),
                    (('this', 'this'), 1),
                ]
            ),
        )
        self.assertEqual(
            sorted(b.word_fd.items()),
            sorted([('a', 2), ('is', 2), ('test', 2), ('this', 2)]),
        )
        self.assertTrue(
            len(sent)
            == sum(b.word_fd.values())
            == (sum(b.ngram_fd.values()) + 4 + 3 + 2 + 1) / 4.0
        )
        self.assertTrue(
            close_enough(
                sorted(b.score_ngrams(BigramAssocMeasures.pmi)),
                sorted(
                    [
                        (('a', 'test'), 1.0),
                        (('is', 'a'), 1.0),
                        (('this', 'is'), 1.0),
                        (('is', 'test'), 0.5849625007211562),
                        (('this', 'a'), 0.5849625007211562),
                        (('a', 'a'), -1.0),
                        (('is', 'is'), -1.0),
                        (('test', 'test'), -1.0),
                        (('this', 'this'), -1.0),
                    ]
                ),
            )
        )
