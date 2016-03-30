# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import unittest

from nltk.model import NgramCounter
from nltk.model.counter import LanguageModelVocabulary


class NgramCounterTests(unittest.TestCase):
    """Tests NgramCounter class"""

    @classmethod
    def setUpClass(self):
        self.trigram_counter = NgramCounter(3, 2, ['abcd', 'egadbe'])
        self.bigram_counter = NgramCounter(2, 2, ['abcd', 'egadbe'])

    def test_NgramCounter_order_property(self):
        self.assertEqual(self.trigram_counter.order, 3)

    def test_NgramCounter_breaks_given_invalid_order(self):
        with self.assertRaises(ValueError) as exc_info:
            NgramCounter(0, 0, ['abc'])
        expected_error_msg = "Order of NgramCounter cannot be less than 1. Got: 0"
        self.assertEqual(str(exc_info.exception), expected_error_msg)

    def test_NgramCounter_vocab_creation(self):
        # more of an integration test
        self.assertTrue('a' in self.bigram_counter.vocabulary)
        self.assertFalse('c' in self.bigram_counter.vocabulary)

    def test_change_vocab_cutoff(self):
        ngram_counter = NgramCounter(2, 2, ['abcd', 'eadbe'])
        ngram_counter.change_vocab_cutoff(1)

        # "c" was seen once so now it should be showing up in the vocab
        self.assertTrue('c' in ngram_counter.vocabulary)

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
            ("<UNK>", "a"),
            ("a", "d"),
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
        expected_count_a = 2

        self.assertEqual(expected_count_a, unigrams['a'])

    def test_unigram_counts_completely_unseen_words(self):
        unigrams = self.bigram_counter.unigrams
        expected_count_a = 0

        self.assertEqual(expected_count_a, unigrams['z'])

    def test_unigram_counts_unknown_words(self):
        # The subtle difference between this and "unseen" is that the latter
        # have no counts recorded for them at all and in practice would usually
        # get converted to "unknown" words
        unigrams = self.bigram_counter.unigrams
        expected_count_a = 2

        self.assertEqual(expected_count_a, unigrams['<UNK>'])


class LanguageModelVocabularyTests(unittest.TestCase):
    """tests LanguageModelVocabulary Class"""

    @classmethod
    def setUpClass(self):
        self.vocab = LanguageModelVocabulary(2, 'zabcfdegadbew')

    def test_cutoff_value_set_correctly(self):
        self.assertEqual(self.vocab.cutoff, 2)

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
