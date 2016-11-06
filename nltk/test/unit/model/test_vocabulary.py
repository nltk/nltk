# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import copy
import unittest

from nltk.model import NgramModelVocabulary


class NgramModelVocabularyTests(unittest.TestCase):
    """tests NgramModelVocabulary Class"""

    @classmethod
    def setUpClass(self):
        self.vocab = NgramModelVocabulary(2, ['z', 'a', 'b', 'c', 'f', 'd',
                                             'e', 'g', 'a', 'd', 'b', 'e', 'w'])

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

    def test_copying_vs_recreating_vocabulary(self):
        new_vocab = NgramModelVocabulary(1, self.vocab)
        copied_vocab = copy.copy(self.vocab)

        # Because of the different cutoff the two must also be unequal
        self.assertNotEqual(new_vocab, self.vocab)
        # Equality test should be True because copies are "equal"
        self.assertEqual(copied_vocab, self.vocab)
