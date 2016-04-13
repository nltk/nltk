# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import division

import unittest

from nltk.model import NgramCounter
from nltk.model.counter import NgramModelVocabulary, EmptyVocabularyError, build_vocabulary
from nltk.model.ngram import BaseNgramModel, NEG_INF


class NgramCounterTests(unittest.TestCase):
    """Tests NgramCounter class"""

    @classmethod
    def setUpClass(self):
        self.vocab = NgramModelVocabulary(2, "abcdeadbe")

        self.trigram_counter = NgramCounter(3, self.vocab)
        self.trigram_counter.count_ngrams(['abcd', 'egdbe'])

        self.bigram_counter = NgramCounter(2, self.vocab)
        self.bigram_counter.count_ngrams(['abcd', 'egdbe'])

    def test_NgramCounter_order_attr(self):
        self.assertEqual(self.trigram_counter.order, 3)

    def test_NgramCounter_breaks_given_invalid_order(self):
        with self.assertRaises(ValueError) as exc_info:
            NgramCounter(0, self.vocab)
        expected_error_msg = "Order of NgramCounter cannot be less than 1. Got: 0"
        self.assertEqual(str(exc_info.exception), expected_error_msg)

    def test_check_against_vocab(self):
        unk_label = "<UNK>"

        self.assertEqual("a", self.bigram_counter.check_against_vocab("a"))
        self.assertEqual(unk_label, self.bigram_counter.check_against_vocab("c"))

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

        bigrams = self.trigram_counter.ngrams[2]
        trigrams = self.trigram_counter.ngrams[3]

        self.assertCountEqual(expected_bigram_contexts, bigrams.conditions())
        self.assertCountEqual(expected_trigram_contexts, trigrams.conditions())

    def test_bigram_counts_seen_ngrams(self):
        bigrams = self.bigram_counter.ngrams[2]
        b_given_a_count = 1
        unk_given_b_count = 1

        self.assertEqual(b_given_a_count, bigrams[('a',)]['b'])
        self.assertEqual(unk_given_b_count, bigrams[('b',)]['<UNK>'])

    def test_bigram_counts_unseen_ngrams(self):
        bigrams = self.bigram_counter.ngrams[2]
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


class NgramModelVocabularyTests(unittest.TestCase):
    """tests NgramModelVocabulary Class"""

    @classmethod
    def setUpClass(self):
        self.vocab = NgramModelVocabulary(2, 'zabcfdegadbew')

    def test_cutoff_value_set_correctly(self):
        self.assertEqual(self.vocab.cutoff, 2)

    def test_cutoff_setter_checks_value(self):
        with self.assertRaises(ValueError) as exc_info:
            NgramModelVocabulary(0, "abc")
        expected_error_msg = "Cutoff value cannot be less than 1. Got: 0"
        self.assertEqual(expected_error_msg, str(exc_info.exception))

    def test_counts_set_correctly(self):
        self.assertEqual(self.vocab['a'], 2)
        self.assertEqual(self.vocab['b'], 2)
        self.assertEqual(self.vocab['c'], 1)

    def test_membership_check_respects_cutoff(self):
        # a was seen 2 times, so it should be considered part of the vocabulary
        self.assertTrue('a' in self.vocab)
        # "c" was seen once, it shouldn't be considered part of the vocab
        self.assertFalse('c' in self.vocab)
        # "z" was never seen at all, also shouldn't be considered in the vocab
        self.assertFalse('z' in self.vocab)

    def test_vocab_len_respects_cutoff(self):
        # Vocab size is the number of unique tokens that occur at least as often
        # as the cutoff value, plus 1 to account for unknown words.
        expected_vocab_size = 5
        self.assertEqual(expected_vocab_size, len(self.vocab))


class BaseNgramModelTests(unittest.TestCase):
    """unit tests for BaseNgramModel class"""

    @classmethod
    def setUpClass(self):
        self.vocab = NgramModelVocabulary(2, "abcabc")
        self.counter = NgramCounter(2, self.vocab)
        self.counter.count_ngrams(['abcd', 'egadbe'])
        # print(self.counter.ngrams[2])
        self.base_model = BaseNgramModel(self.counter)

    def test_score(self):
        # this should return the relative frequency of the word
        score1 = self.base_model.score("b", ["a"])
        score2 = self.base_model.score("c", ["a"])
        score3 = self.base_model.score("c", ["a", "d"])
        self.assertEqual(score1, 0.5)
        self.assertEqual(score1, score2)
        self.assertEqual(score1, score3)

    def test_logscore_non_zero_score(self):
        logscore = self.base_model.logscore("g", ["e"])
        self.assertEqual(logscore, -1.0)

    def test_logscore_zero_score(self):
        model = BaseNgramModel(self.counter)
        model.score = lambda word, context: 0.0
        logscore = model.logscore("d", ["e"])
        self.assertEqual(logscore, NEG_INF)


class ModelFuncsTests(unittest.TestCase):
    """Tests for module functions"""

    def test_build_vocabulary(self):
        vocab = build_vocabulary(2, 'zabcfdegadbew')
        assert "a" in vocab
        assert "c" not in vocab

    def test_build_vocabulary_multiple_texts(self):
        vocab = build_vocabulary(2, 'zabcfdegadbew', "abcdeadbe")
        assert "a" in vocab
        assert "c" in vocab
        assert "g" not in vocab

    def test_build_vocabulary_no_texts(self):
        vocab = build_vocabulary(2)
        assert "a" not in vocab
        assert "z" not in vocab
