# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import division
import unittest

from six import add_metaclass
from nltk.util import everygrams
from nltk.model import NgramCounter, NgramModelVocabulary
from nltk.model.smoothing import WittenBell


class ParametrizeTestsMeta(type):
    """Metaclass for generating parametrized tests."""
    def __new__(cls, name, bases, dct):
        alphas = dct.get("alpha_tests", [])
        for i, (word, context, expected_score) in enumerate(alphas):
            dct["test_alpha_{0}".format(i)] = cls.add_alpha_test(word, context, expected_score)
        gammas = dct.get("gamma_tests", [])
        for i, (context, expected_score) in enumerate(gammas):
            dct["test_gamma_{0}".format(i)] = cls.add_gamma_test(context, expected_score)
        betas = dct.get("beta_tests", [])
        for i, (word, context, expected_score) in enumerate(betas):
            dct["test_beta_{0}".format(i)] = cls.add_beta_test(word, context, expected_score)
        return super(ParametrizeTestsMeta, cls).__new__(cls, name, bases, dct)

    @classmethod
    def add_alpha_test(cls, word, context, expected_score):

        def test_method(self):
            self.assertAlmostEqual(
                self.smoothing.alpha(word, context),
                expected_score,
                msg="word='{0}', context={1}".format(word, context),
                places=4)

        return test_method

    @classmethod
    def add_gamma_test(cls, context, expected_score):

        def test_method(self):
            self.assertAlmostEqual(
                self.smoothing.gamma(context),
                expected_score,
                msg="context={}".format(context),
                places=4)

        return test_method

    @classmethod
    def add_beta_test(cls, word, context, expected_score):

        def test_method(self):
            self.assertAlmostEqual(
                self.smoothing.beta(word, context),
                expected_score,
                msg="word='{0}', context={1}".format(word, context),
                places=4)

        return test_method


@add_metaclass(ParametrizeTestsMeta)
class WittenBellTests(unittest.TestCase):
    """Doctests for WittenBell smoothing."""

    gamma_tests = [
        # N bigrams = 8
        # N+(['c']) = 1
        (['c'], 1 / 9)
    ]
    alpha_tests = [
        # gamma(['c']) = 1 / 9
        # MLE('d' | 'c') = 1
        # p('d' | 'c') = (1 - 1/9) * 1
        ('d', ['c'], 8 / 9),
        # Being based on MLE, this returns 0 for unseen items
        ('b', ['c'], 0),
    ]
    beta_tests = [
        # Beta is currently MLE
        ('d', ['c'], 1),
        # Being based on MLE, this returns 0 for unseen items
        ('b', ['c'], 0),
        # can also handle unigrams
        ('b', None, 2 / 10),
        ('<UNK>', None, 3 / 10)

    ]

    def setUp(self):
        vocab = NgramModelVocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)
        training_text = [list('abcd'), list('egadbe')]
        counter = NgramCounter((everygrams(list(vocab.lookup(sent)), max_len=2)
                                for sent in training_text))
        self.smoothing = WittenBell(counter, vocab)

    def test_recurse(self):
        self.assertEqual(self.smoothing.recurse(['c']), [0])
        self.assertEqual(self.smoothing.recurse(['c', 'b']), [0, 1])
        self.assertEqual(self.smoothing.recurse('abcd'), [0, 1, 2, 3])
