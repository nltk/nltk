# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import unittest

from nltk import six

from nltk.model import NgramModelVocabulary, NgramCounter
from nltk.model.util import check_ngram_order, POS_INF
from nltk.model.testutil import NgramCounterSetUpMixin


class NgramCounterBaseTest(unittest.TestCase, NgramCounterSetUpMixin):
    """Sets up vocabulary and adds a useful method with mixin"""

    @classmethod
    def setUpClass(cls):
        cls.vocab = NgramModelVocabulary(["a", "b", "c", "d", "e",
                                          "a", "d", "b", "e"], unk_cutoff=2)


class NgramCounterTests(NgramCounterBaseTest):
    """Tests for NgramCounter that only involve lookup, no modification."""

    @classmethod
    def setUpClass(cls):
        super(NgramCounterTests, cls).setUpClass()

        text = ['abcd', 'egdbe']
        cls.trigram_counter = cls.setUpNgramCounter(3, text)
        cls.bigram_counter = cls.setUpNgramCounter(2, text)

    def test_NgramCounter_order_attr(self):
        self.assertEqual(self.trigram_counter.order, 3)

    def test_ngram_order_access_unigrams(self):
        self.assertEqual(self.bigram_counter[1], self.bigram_counter.unigrams)

    def test_ngram_order_access_order_too_high(self):
        with self.assertRaises(ValueError):
            self.bigram_counter[3]

    def test_NgramCounter_breaks_given_invalid_order(self):
        with self.assertRaises(ValueError) as exc_info:
            NgramCounter(0, self.vocab)

    def test_NgramCounter_breaks_given_empty_vocab(self):
        empty_vocab = NgramModelVocabulary("abc", unk_cutoff=2)
        empty_counter = NgramCounter(2, empty_vocab)

        with self.assertRaises(ValueError) as exc_info:
            empty_counter.train_counts(['ad', 'hominem'])

        self.assertEqual(("Cannot start counting ngrams until "
                          "vocabulary contains more than one item."),
                         str(exc_info.exception))

    def test_ngram_conditional_freqdist(self):
        expected_trigram_contexts = [
            ("<s>", "<s>"),
            ("<s>", "a"),
            ("a", "b"),
            ("b", "<UNK>"),
            ("<UNK>", "d"),
            ("d", "</s>"),
            ("<s>", "e"),
            ("e", "<UNK>"),
            ("d", "b"),
            ("b", "e"),
            ("e", "</s>",)
        ]
        expected_bigram_contexts = [
            ("a",),
            ("b",),
            ("d",),
            ("e",),
            ("<UNK>",),
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
        self.assertEqual(unk_given_b_count, bigrams[('b',)]['<UNK>'])

    def test_bigram_counts_unseen_ngrams(self):
        bigrams = self.bigram_counter[2]
        c_given_b_count = 0

        self.assertEqual(c_given_b_count, bigrams[('b',)]['c'])

    def test_unigram_counts_seen_words(self):
        unigrams = self.bigram_counter.unigrams
        expected_count_b = 2

        self.assertEqual(expected_count_b, unigrams['b'])

    def test_unigram_counts_completely_unseen_words(self):
        unigrams = self.bigram_counter.unigrams
        unseen_count = 0

        self.assertEqual(unseen_count, unigrams['z'])

    def test_unigram_counts_unknown_words(self):
        # The subtle difference between this and "unseen" is that the latter
        # have no counts recorded for them at all and in practice would usually
        # get assigned the "unknown" label
        unigrams = self.bigram_counter.unigrams
        unknown_count = 2

        self.assertEqual(unknown_count, unigrams['<UNK>'])


class NgramCounterModificationTests(NgramCounterBaseTest):
    """These tests require a fresh instance of NgramCounter per method."""

    def setUp(self):
        text = ['abcd', 'egdbe']
        self.bigram_counter = self.setUpNgramCounter(2, text)

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
