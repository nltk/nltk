# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import unittest

from nltk import six

from nltk.model import NgramModelVocabulary, NgramCounter
from util import mask_oov_words_in_corpus


class NgramCounterTests(unittest.TestCase):
    """Tests NgramCounter class"""

    @classmethod
    def setUpClass(self):
        self.vocab = NgramModelVocabulary(["a", "b", "c", "d", "e",
                                           "a", "d", "b", "e"], unk_cutoff=2)
        normalized = mask_oov_words_in_corpus(['abcd', 'egdbe'], self.vocab)

        self.trigram_counter = NgramCounter(3, self.vocab)
        self.trigram_counter.train_counts(normalized)

        self.bigram_counter = NgramCounter(2, self.vocab)
        self.bigram_counter.train_counts(normalized)

    def test_NgramCounter_order_attr(self):
        self.assertEqual(self.trigram_counter.order, 3)

    def test_NgramCounter_breaks_given_invalid_order(self):
        with self.assertRaises(ValueError) as exc_info:
            NgramCounter(0, self.vocab)
        expected_error_msg = "Order of NgramCounter cannot be less than 1. Got: 0"
        self.assertEqual(str(exc_info.exception), expected_error_msg)

    def test_NgramCounter_breaks_given_empty_vocab(self):
        empty_vocab = NgramModelVocabulary("abc", unk_cutoff=2)
        empty_counter = NgramCounter(2, empty_vocab, pad_left=False, pad_right=False)

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

        bigrams = self.trigram_counter.ngrams[2]
        trigrams = self.trigram_counter.ngrams[3]

        six.assertCountEqual(self, expected_bigram_contexts, bigrams.conditions())
        six.assertCountEqual(self, expected_trigram_contexts, trigrams.conditions())

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
