# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import division
import unittest
import math

from six import add_metaclass

from nltk.model import (Vocabulary, MleLanguageModel, LidstoneNgramModel, LaplaceNgramModel)
from nltk.model.util import NEG_INF


class ParametrizeTestsMeta(type):
    """Metaclass for generating parametrized tests."""

    def __new__(cls, name, bases, dct):
        contexts = (('a',), ('c',), (u'<s>',), ('b',), (u'<UNK>',), ('d',), ('e',), ('r',), ('w',))
        for i, c in enumerate(contexts):
            dct["test_sumto1_{0}".format(i)] = cls.add_sum_to_1_test(c)
        scores = dct.get("score_tests", [])
        for i, (word, context, expected_score) in enumerate(scores):
            dct["test_score_{0}".format(i)] = cls.add_score_test(word, context, expected_score)
        return super(ParametrizeTestsMeta, cls).__new__(cls, name, bases, dct)

    @classmethod
    def add_score_test(cls, word, context, expected_score):

        def test_method(self):
            self.assertAlmostEqual(
                self.model.score(word, context),
                expected_score,
                msg="word='{0}', context={1}".format(word, context),
                places=4)

        return test_method

    @classmethod
    def add_sum_to_1_test(cls, context):

        def test(self):
            s = sum(self.model.score(w, context) for w in self.model.vocab)
            self.assertAlmostEqual(s, 1.0, msg="The context is {}".format(context))

        return test


class ScoreTestHelper(object):
    """Shared tests and helper code specifically for bigram models."""

    def assertIsNan(self, value):
        self.assertTrue(math.isnan(value))


@add_metaclass(ParametrizeTestsMeta)
class MleBigramModelTests(unittest.TestCase, ScoreTestHelper):
    """unit tests for MLENgramModel class"""

    score_tests = [
        ("d", ["c"], 1),
        # Unseen ngrams should yield 0
        ("d", ["e"], 0),
        # Unigrams should also be 0
        ("z", None, 0),
        # N unigrams = 14
        # count('a') = 2
        ('a', None, 2. / 14),
        # count('y') = 3
        ('y', None, 3. / 14),
    ]

    def setUp(self):
        vocab = Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)
        training_text = [list('abcd'), list('egadbe')]
        self.model = MleLanguageModel(2, vocabulary=vocab)
        self.model.fit(training_text)

    def test_logscore_zero_score(self):
        # logscore of unseen ngrams should be -inf
        logscore = self.model.logscore("d", ["e"])

        self.assertEqual(logscore, NEG_INF)

    def test_entropy_perplexity_seen(self):
        # ngrams seen during training
        trained = [('<s>', 'a'),
                   ('a', 'b'),
                   ('b', '<UNK>'),
                   ('<UNK>', 'a'),
                   ('a', 'd'),
                   ('d', '</s>')]
        # Ngram = score; Log score; product
        # <s>, a    = 0.5; -1; -0.5
        # a, b      = 0.5; -1; -0.5
        # b, UNK    = 0.5; -1; -0.5
        # UNK, a    = 0.(3); -1.585; -0.5283
        # a, d      = 0.5; -1; -0.5
        # d, </s>   = 0.5; -1; -0.5
        # TOTAL products   = -3.0283
        H = 3.0283
        perplexity = 8.1586

        self.assertAlmostEqual(H, self.model.entropy(trained), places=4)
        self.assertAlmostEqual(perplexity, self.model.perplexity(trained), places=4)

    def test_entropy_perplexity_unseen(self):
        # In MLE, even one unseen ngram should turn entropy and perplexity into NaN
        untrained = [('<s>', 'a'),
                     ('a', 'c'),
                     ('c', 'd'),
                     ('d', '</s>')]

        self.assertIsNan(self.model.entropy(untrained))
        self.assertIsNan(self.model.perplexity(untrained))

    def test_entropy_perplexity_unigrams(self):
        # word = score, log score, product
        # <s>   = 0.1429, -2.8074, -0.4011
        # a     = 0.1429, -2.8074, -0.4011
        # c     = 0.0714, -3.8073, -0.2720
        # UNK   = 0.2143, -2.2224, -0.4762
        # d     = 0.1429, -2.8074, -0.4011
        # c     = 0.0714, -3.8073, -0.2720
        # </s>  = 0.1429, -2.8074, -0.4011
        # Total product = -2.6243
        H = 2.6243
        perplexity = 6.166

        text = [("<s>",), ("a",), ("c",), ("-",),
                ("d",), ("c",), ("</s>",)]

        self.assertAlmostEqual(H, self.model.entropy(text), places=4)
        self.assertAlmostEqual(perplexity, self.model.perplexity(text), places=4)


@add_metaclass(ParametrizeTestsMeta)
class MleTrigramModelTests(unittest.TestCase, ScoreTestHelper):
    """MLE trigram model tests"""

    score_tests = [
        # count(d | b, c) = 1
        # count(b, c) = 1
        ("d", ("b", "c"), 1),
        # count(d | c) = 1
        # count(c) = 1
        ("d", ["c"], 1),
        # total number of tokens is 18, of which "a" occured 2 times
        ("a", None, 2.0 / 18),
        # in vocabulary but unseen
        ("z", None, 0),
        # out of vocabulary should use "UNK" score
        ("y", None, 3.0 / 18)
    ]

    def setUp(self):
        vocab = Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)
        training_text = [list('abcd'), list('egadbe')]
        self.model = MleLanguageModel(3, vocabulary=vocab)
        self.model.fit(training_text)


@add_metaclass(ParametrizeTestsMeta)
class LidstoneBigramModelTests(unittest.TestCase, ScoreTestHelper):
    """unit tests for LidstoneNgramModel class"""

    score_tests = [
        # count(d | c) = 1
        # *count(d | c) = 1.1
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 1.8
        ('d', ['c'], 1.1 / 1.8),
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 0.8 = 14.8
        # count("a") = 2
        # *count("a") = 2.1
        ('a', None, 2.1 / 14.8),
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 0.1
        ('z', None, 0.1 / 14.8),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 3.1
        ('y', None, 3.1 / 14.8),
    ]

    def setUp(self):
        vocab = Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)
        training_text = [list('abcd'), list('egadbe')]
        self.model = LidstoneNgramModel(0.1, 2, vocabulary=vocab)
        self.model.fit(training_text)

    def test_gamma(self):
        self.assertEqual(0.1, self.model.gamma)

    def test_entropy_perplexity(self):
        text = [('<s>', 'a'),
                ('a', 'c'),
                ('c', '<UNK>'),
                ('<UNK>', 'd'),
                ('d', 'c'),
                ('c', '</s>')]
        # Unlike MLE this should be able to handle completely novel ngrams
        # Ngram = score, log score, product
        # <s>, a    = 0.3929, -1.3479, -0.5295
        # a, c      = 0.0357, -4.8074, -0.1717
        # c, UNK      = 0.0556, -4.1699, -0.2317
        # UNK, d      = 0.0263,  -5.2479, -0.1381
        # d, c      = 0.0357, -4.8074, -0.1717
        # c, </s>   = 0.0556, -4.1699, -0.2317
        # Total product: -1.4744
        H = 1.4744
        perplexity = 2.7786
        self.assertAlmostEqual(H, self.model.entropy(text), places=4)
        self.assertAlmostEqual(perplexity, self.model.perplexity(text), places=4)


@add_metaclass(ParametrizeTestsMeta)
class LidstoneTrigramModelTests(unittest.TestCase, ScoreTestHelper):

    score_tests = [
        # Logic behind this is the same as for bigram model
        ('d', ['c'], 1.1 / 1.8),
        # if we choose a word that hasn't appeared after (b, c)
        ('e', ['c'], 0.1 / 1.8),
        # Trigram score now
        ('d', ['b', 'c'], 1.1 / 1.8),
        ('e', ['b', 'c'], 0.1 / 1.8),
    ]

    def setUp(self):
        vocab = Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)
        training_text = [list('abcd'), list('egadbe')]
        self.model = LidstoneNgramModel(0.1, 3, vocabulary=vocab)
        self.model.fit(training_text)


@add_metaclass(ParametrizeTestsMeta)
class LaplaceBigramModelTests(unittest.TestCase, ScoreTestHelper):
    """unit tests for LaplaceNgramModel class"""

    score_tests = [
        # basic sanity-check:
        # count(d | c) = 1
        # *count(d | c) = 2
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 9
        ('d', ['c'], 2. / 9),
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 8 = 22
        # count("a") = 2
        # *count("a") = 3
        ('a', None, 3. / 22),
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 1
        ('z', None, 1. / 22),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 4
        ('y', None, 4. / 22)
    ]

    def setUp(self):
        vocab = Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)
        training_text = [list('abcd'), list('egadbe')]
        self.model = LaplaceNgramModel(2, vocabulary=vocab)
        self.model.fit(training_text)

    def test_gamma(self):
        # Make sure the gamma is set to 1
        self.assertEqual(1, self.model.gamma)

    def test_entropy_perplexity(self):
        text = [('<s>', 'a'),
                ('a', 'c'),
                ('c', '<UNK>'),
                ('<UNK>', 'd'),
                ('d', 'c'),
                ('c', '</s>')]
        # Unlike MLE this should be able to handle completely novel ngrams
        # Ngram = score, log score, product
        # <s>, a    = 0.(2), -2.1699, -0.4339
        # a, c      = 0.(1), -3.1699, -0.3169
        # c, UNK      = 0.125, -3.0, -0.375
        # UNK, d      = 0.1,  -3.3219, -0.3321
        # d, c      = 0.(1) -3.1699, -0.3169
        # c, </s>   = 0.125, -3.0, -0.375
        # Total product: -2.1498
        H = 2.1477
        perplexity = 4.4312
        self.assertAlmostEqual(H, self.model.entropy(text), places=4)
        self.assertAlmostEqual(perplexity, self.model.perplexity(text), places=4)


class NgramModelTextGenerationTests(unittest.TestCase):
    """Using MLE estimator, generate some text."""

    def setUp(self):
        vocab = Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1)
        training_text = [list('abcd'), list('egadbe')]
        self.model = MleLanguageModel(3, vocabulary=vocab)
        self.model.fit(training_text)

    def test_generate_one_no_context(self):
        generated = self.model.generate_one()
        self.assertIn(generated, self.model.counts.unigrams)

    def test_generate_one_small_context(self):
        context = ("c",)
        generated = self.model.generate_one(context=context)

        self.assertIn(generated, self.model.counts[2][context])

    def test_generate_one_normal_context(self):
        context = ("b", "c")
        generated = self.model.generate_one(context=context)

        self.assertIn(generated, self.model.counts[3][context])

    def test_generate_one_backoff_to_smaller_context(self):
        context_no_samples = ("a", "c")
        expected_samples = self.model.counts[2][("c",)]
        generated = self.model.generate_one(context_no_samples)

        self.assertIn(generated, expected_samples)

    def test_generate_one_backoff_to_unigrams(self):
        context_no_samples = ("a", "</s>")
        expected_samples = self.model.counts.unigrams
        generated = self.model.generate_one(context_no_samples)

        self.assertIn(generated, expected_samples)

    def test_generate_no_seed_unigrams(self):
        generated_text = self.model.generate(5)

        self.assertEqual(5, len(generated_text))
        # With no seed, first item should be one of unigrams
        self.assertIn(generated_text[0], self.model.counts[1])

    def test_generate_with_bigram_seed(self):
        # seed has to be picked so as to make the test deterministic!
        seed = ("c",)
        seed_continuations = self.model.counts[2][seed]
        generated_text = self.model.generate(5, seed=seed)

        # seed should be the first item
        self.assertEqual(generated_text[0], seed[0])
        # Second item should depend on seed
        self.assertIn(generated_text[1], seed_continuations)
