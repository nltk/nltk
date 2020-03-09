# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2020 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import unittest

from nltk import FreqDist
from nltk.lm import NgramCounter
from nltk.util import everygrams


class NgramCounterTests(unittest.TestCase):
    """Tests for NgramCounter that only involve lookup, no modification."""

    @classmethod
    def setUpClass(cls):

        text = [list("abcd"), list("egdbe")]
        cls.trigram_counter = NgramCounter(
            (everygrams(sent, max_len=3) for sent in text)
        )
        cls.bigram_counter = NgramCounter(
            (everygrams(sent, max_len=2) for sent in text)
        )

    def test_N(self):
        self.assertEqual(self.bigram_counter.N(), 16)
        self.assertEqual(self.trigram_counter.N(), 21)

    def test_counter_len_changes_with_lookup(self):
        self.assertEqual(len(self.bigram_counter), 2)
        _ = self.bigram_counter[50]
        self.assertEqual(len(self.bigram_counter), 3)

    def test_ngram_order_access_unigrams(self):
        self.assertEqual(self.bigram_counter[1], self.bigram_counter.unigrams)

    def test_ngram_conditional_freqdist(self):
        expected_trigram_contexts = [
            ("a", "b"),
            ("b", "c"),
            ("e", "g"),
            ("g", "d"),
            ("d", "b"),
        ]
        expected_bigram_contexts = [("a",), ("b",), ("d",), ("e",), ("c",), ("g",)]

        bigrams = self.trigram_counter[2]
        trigrams = self.trigram_counter[3]

        self.assertCountEqual(expected_bigram_contexts, bigrams.conditions())
        self.assertCountEqual(expected_trigram_contexts, trigrams.conditions())

    def test_bigram_counts_seen_ngrams(self):
        b_given_a_count = 1
        unk_given_b_count = 1

        self.assertEqual(b_given_a_count, self.bigram_counter[["a"]]["b"])
        self.assertEqual(unk_given_b_count, self.bigram_counter[["b"]]["c"])

    def test_bigram_counts_unseen_ngrams(self):
        z_given_b_count = 0

        self.assertEqual(z_given_b_count, self.bigram_counter[["b"]]["z"])

    def test_unigram_counts_seen_words(self):
        expected_count_b = 2

        self.assertEqual(expected_count_b, self.bigram_counter["b"])

    def test_unigram_counts_completely_unseen_words(self):
        unseen_count = 0

        self.assertEqual(unseen_count, self.bigram_counter["z"])


class NgramCounterTrainingTests(unittest.TestCase):
    def setUp(self):
        self.counter = NgramCounter()

    def test_empty_string(self):
        test = NgramCounter("")
        self.assertNotIn(2, test)
        self.assertEqual(test[1], FreqDist())

    def test_empty_list(self):
        test = NgramCounter([])
        self.assertNotIn(2, test)
        self.assertEqual(test[1], FreqDist())

    def test_None(self):
        test = NgramCounter(None)
        self.assertNotIn(2, test)
        self.assertEqual(test[1], FreqDist())

    def test_train_on_unigrams(self):
        words = list("abcd")
        counter = NgramCounter([[(w,) for w in words]])

        self.assertFalse(bool(counter[3]))
        self.assertFalse(bool(counter[2]))
        self.assertCountEqual(words, counter[1].keys())

    def test_train_on_illegal_sentences(self):
        str_sent = ["Check", "this", "out", "!"]
        list_sent = [["Check", "this"], ["this", "out"], ["out", "!"]]

        with self.assertRaises(TypeError):
            NgramCounter([str_sent])

        with self.assertRaises(TypeError):
            NgramCounter([list_sent])

    def test_train_on_bigrams(self):
        bigram_sent = [("a", "b"), ("c", "d")]
        counter = NgramCounter([bigram_sent])

        self.assertFalse(bool(counter[3]))

    def test_train_on_mix(self):
        mixed_sent = [("a", "b"), ("c", "d"), ("e", "f", "g"), ("h",)]
        counter = NgramCounter([mixed_sent])
        unigrams = ["h"]
        bigram_contexts = [("a",), ("c",)]
        trigram_contexts = [("e", "f")]

        self.assertCountEqual(unigrams, counter[1].keys())
        self.assertCountEqual(bigram_contexts, counter[2].keys())
        self.assertCountEqual(trigram_contexts, counter[3].keys())
