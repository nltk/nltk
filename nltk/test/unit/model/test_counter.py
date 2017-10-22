# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import unittest

from nltk import six

from nltk.model import NgramModelVocabulary, NgramCounter
from nltk.model.util import check_ngram_order, POS_INF, default_ngrams


class NgramCounterTests(unittest.TestCase):
    """Tests for NgramCounter that only involve lookup, no modification."""

    @classmethod
    def setUpClass(cls):

        text = [list('abcd'), list('egdbe')]
        cls.trigram_counter = NgramCounter(3)
        cls.trigram_counter.train_counts(map(default_ngrams(3), text))
        cls.bigram_counter = NgramCounter(2)
        cls.bigram_counter.train_counts(map(default_ngrams(2), text))

    def test_NgramCounter_order_attr(self):
        self.assertEqual(self.trigram_counter.order, 3)

    def test_ngram_order_access_unigrams(self):
        self.assertEqual(self.bigram_counter[1], self.bigram_counter.unigrams)

    def test_ngram_order_access_order_too_high(self):
        with self.assertRaises(ValueError):
            self.bigram_counter[3]

    def test_NgramCounter_breaks_given_invalid_order(self):
        with self.assertRaises(ValueError) as exc_info:
            NgramCounter(0)

    def test_ngram_conditional_freqdist(self):
        expected_trigram_contexts = [
            ("<s>", "<s>"),
            ("<s>", "a"),
            ("a", "b"),
            ("b", "c"),
            ("c", "d"),
            ("d", "</s>"),
            ("<s>", "e"),
            ("e", "g"),
            ("g", "d"),
            ("d", "b"),
            ("b", "e"),
            ("e", "</s>",)
        ]
        expected_bigram_contexts = [
            ("a",),
            ("b",),
            ("d",),
            ("e",),
            ("c",),
            ("g",),
            ("<s>",),
            ("</s>",)
        ]

        bigrams = self.trigram_counter[2]
        trigrams = self.trigram_counter[3]

        six.assertCountEqual(self, expected_bigram_contexts, bigrams.conditions())
        six.assertCountEqual(self, expected_trigram_contexts, trigrams.conditions())

    def test_bigram_counts_seen_ngrams(self):
        bigrams = self.bigram_counter[2]
        b_given_a_count = 1
        unk_given_b_count = 1

        self.assertEqual(b_given_a_count, bigrams[('a',)]['b'])
        self.assertEqual(unk_given_b_count, bigrams[('b',)]['c'])

    def test_bigram_counts_unseen_ngrams(self):
        bigrams = self.bigram_counter[2]
        z_given_b_count = 0

        self.assertEqual(z_given_b_count, bigrams[('b',)]['z'])

    def test_unigram_counts_seen_words(self):
        unigrams = self.bigram_counter.unigrams
        expected_count_b = 2

        self.assertEqual(expected_count_b, unigrams['b'])

    def test_unigram_counts_completely_unseen_words(self):
        unigrams = self.bigram_counter.unigrams
        unseen_count = 0

        self.assertEqual(unseen_count, unigrams['z'])


class NgramCounterModificationTests(unittest.TestCase):
    """These tests require a fresh instance of NgramCounter per method."""

    def setUp(self):
        text = [list('abcd'), list('egdbe')]
        self.bigram_counter = NgramCounter(2)
        self.bigram_counter.train_counts(map(default_ngrams(2), text))

    def test_NgramCounter_train_wrong_ngram_size(self):
        trigrams = [[
                    (1, 2, 3),
                    (4, 5, 6)
                    ]]
        with self.assertRaises(ValueError):
            self.bigram_counter.train_counts(trigrams)


class CheckNgramOrderTests(unittest.TestCase):
    """Cases for check_ngram_order function"""

    def test_sane_inputs(self):
        self.assertEqual(3, check_ngram_order(3))
        self.assertEqual(3, check_ngram_order(3, max_order=5))

    def test_pos_inf_input(self):
        with self.assertRaises(ValueError):
            check_ngram_order(POS_INF)

    def test_inputs_less_than_one(self):
        with self.assertRaises(ValueError):
            check_ngram_order(0)

        with self.assertRaises(ValueError):
            check_ngram_order(-5)


class TrigramCounterDifferentInputs(unittest.TestCase):

    def setUp(self):
        self.counter = NgramCounter(3)

    def test_train_on_unigrams(self):
        words = list("abcd")
        unigram_sent = [(w,) for w in words]
        self.counter.train_counts([unigram_sent])

        self.assertFalse(bool(self.counter[3]))
        self.assertFalse(bool(self.counter[2]))
        six.assertCountEqual(self, words, self.counter[1].keys())

    def test_train_on_illegal_sentences(self):
        str_sent = ['Check', 'this', 'out', '!']
        list_sent = [["Check", "this"], ["this", "out"], ["out", "!"]]

        with self.assertRaises(TypeError):
            self.counter.train_counts([str_sent])

        with self.assertRaises(TypeError):
            self.counter.train_counts([list_sent])

    def test_train_on_bigrams(self):
        bigram_sent = [("a", 'b'), ("c", "d")]
        self.counter.train_counts([bigram_sent])

        self.assertFalse(bool(self.counter[3]))

    def test_train_on_mix(self):
        mixed_sent = [("a", 'b'), ("c", "d"), ("e", "f", "g"), ("h",)]
        self.counter.train_counts([mixed_sent])
        unigrams = ["h"]
        bigram_contexts = [("a",), ("c",)]
        trigram_contexts = [("e", "f")]

        six.assertCountEqual(self, unigrams, self.counter[1].keys())
        six.assertCountEqual(self, bigram_contexts, self.counter[2].keys())
        six.assertCountEqual(self, trigram_contexts, self.counter[3].keys())
