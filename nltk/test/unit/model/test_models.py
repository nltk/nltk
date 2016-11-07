# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import division
import unittest

from nltk.model import (build_vocabulary,
                        count_ngrams,
                        NgramModelVocabulary,
                        NgramCounter,
                        BaseNgramModel,
                        MLENgramModel,
                        LidstoneNgramModel,
                        LaplaceNgramModel)
from nltk.model.util import NEG_INF
from nltk.model.testutil import NgramCounterSetUpMixin


class NgramModelBaseTest(unittest.TestCase, NgramCounterSetUpMixin):
    """Base test class for testing ngram model classes"""

    @classmethod
    def setUpClass(cls):
        # The base vocabulary contains 5 items: abcd and UNK
        cls.vocab = NgramModelVocabulary(["a", "b", "c", "d"], unk_cutoff=1)
        # NgramCounter.vocabulary contains 7 items (+2 for padding symbols)
        cls.counter = cls.setUpNgramCounter(2, ['abcd', 'egadbe'])

    def total_vocab_score(self, context):
        """Sums up scores for the whole vocabulary given some context.

        Used to make sure they sum to 1.
        Note that we *must* loop over the counter's vocabulary so as to include
        padding symbols.
        """
        return sum(self.model.score(w, context) for w in self.vocab)


class BaseNgramModelTests(NgramModelBaseTest):
    """unit tests for BaseNgramModel class"""

    def setUp(self):
        self.model = BaseNgramModel(self.counter)

    def test_context_checker(self):
        ctx_tuple = self.model.check_context(('a',))
        ctx_list = self.model.check_context(['a'])

        self.assertEqual(ctx_list, ctx_tuple)

        with self.assertRaises(ValueError):
            self.model.check_context(['a', 'b'])

        with self.assertRaises(TypeError):
            self.model.check_context(None)

    def test_score(self):
        with self.assertRaises(NotImplementedError):
            self.model.score("d", ["c"])


def bigram_model(cls):
    """Decorator for adding bigram model testing helpers"""

    handles_unseens = getattr(cls, "handles_unseens", True)

    if handles_unseens:
        contexts = (('a',), ('c',), (u'<s>',), ('b',), (u'<UNK>',), ('d',),
                    ('e',), ('r'), ('w',))
    else:
        contexts = (('a',), ('c',), (u'<s>',), ('b',), (u'<UNK>',), ('d',))

    def score_assertions(self, expected_score):
        """Helper function for testing an ngram model's score method."""
        got_score_list = self.model.score("d", ["c"])
        got_score_tuple = self.model.score("d", ("c",))

        self.assertAlmostEqual(expected_score, got_score_list, places=4)
        self.assertEqual(got_score_list, got_score_tuple)

    def entropy_perp_assertions(self, H, perplexity, corpus="ac-dc"):
        """Helper function for testing entropy/perplexity."""
        self.assertAlmostEqual(H, self.model.entropy(corpus), places=4)
        self.assertAlmostEqual(perplexity, self.model.perplexity(corpus),
                               places=4)

    def test_score_context_too_long(self):
        with self.assertRaises(ValueError) as exc_info:
            self.model.score('d', ('a', 'b'))

    def test_scores_sum_to_1(self):
        # Laplace (like Lidstone) smoothing can handle contexts unseen during training
        for context in contexts:
            self.assertAlmostEqual(self.total_vocab_score(context), 1)

    cls.test_score_context_too_long = test_score_context_too_long
    cls.score_assertions = score_assertions
    cls.entropy_perp_assertions = entropy_perp_assertions
    cls.test_scores_sum_to_1 = test_scores_sum_to_1
    return cls


@bigram_model
class MLENgramModelTests(NgramModelBaseTest):
    """unit tests for MLENgramModel class"""
    handles_unseens = False

    def setUp(self):
        self.model = MLENgramModel(self.counter)

    def test_score(self):
        self.score_assertions(1)

    def test_score_unseen(self):
        # Unseen ngrams should yield 0
        score_unseen = self.model.score("d", ["e"])

        self.assertEqual(score_unseen, 0)

    def test_score_sum_of_unseen_contexts_is_0(self):
        # MLE will give 0 scores across the board for contexts not seen during training.
        # Note that due to heavy defaultdict usage this doesn't raise missing key errors.
        unseen_contexts = (('e',), ('r',))

        for context in unseen_contexts:
            self.assertEqual(self.total_vocab_score(context), 0)

    def test_logscore_zero_score(self):
        # logscore of unseen ngrams should be -inf
        logscore = self.model.logscore("d", ["e"])

        self.assertEqual(logscore, NEG_INF)

    @unittest.skip
    def test_entropy(self):
        # ngrams seen during training
        seen_ngrams = "abrad"
        # Ngram = Log score
        # <s>, a    = -1
        # a, b      = -1
        # b, UNK    = -1
        # UNK, a    = -1.585
        # a, d      = -1
        # d, </s>   = -1
        # TOTAL    = -6.585
        seen_entropy = 1.0975

        self.assertAlmostEqual(seen_entropy, self.model.entropy(seen_ngrams), places=4)

    @unittest.skip
    def test_entropy_perplexity_unseen(self):
        # In MLE, even one unseen ngram should turn entropy and perplexity into INF
        unseen_ngram = "acd"

        self.assertEqual(float("inf"), self.model.entropy(unseen_ngram))
        self.assertEqual(float("inf"), self.model.perplexity(unseen_ngram))


@bigram_model
class LidstoneNgramModelTests(NgramModelBaseTest):
    """unit tests for LidstoneNgramModel class"""

    def setUp(self):
        self.model = LidstoneNgramModel(0.1, self.counter)

    def test_gamma_and_gamma_norm(self):
        self.assertEqual(0.1, self.model.gamma)
        # There are 7 items in the vocabulary, so we expect gamma norm to be 0.7
        # Due to floating point funkyness in Python, we use float assertion here
        self.assertAlmostEqual(0.7, self.model.gamma_norm)

    def test_score(self):
        # count(d | c) = 1
        # *count(d | c) = 1.1
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 1.7
        self.score_assertions(0.6471)

    @unittest.skip
    def test_entropy_perplexity(self):
        # Unlike MLE this should be able to handle completely novel ngrams
        test_corp = "ac-dc"
        # Ngram = score; log score
        # <s>, a    = 0.4074; -1.2955
        # a, c      = 0.1428; -4.7549
        # c, -      = 0.0588; -4.0875
        # -, d      = 0.027;  -5.2109
        # d, c      = 0.037; -4.7563
        # c, </s>   = 0.0588; -4.088
        # Total Log Score: -24.1896
        expected_H = 4.0316
        expected_perplexity = 16.3543
        self.entropy_perp_assertions(expected_H, expected_perplexity)


@bigram_model
class LaplaceNgramModelTests(NgramModelBaseTest):
    """unit tests for LaplaceNgramModel class"""

    def setUp(self):
        self.model = LaplaceNgramModel(self.counter)

    def test_gamma(self):
        # Make sure the gamma is set to 1
        self.assertEqual(1, self.model.gamma)
        # Laplace Gamma norm is just the vocabulary size
        self.assertEqual(7, self.model.gamma_norm)

    def test_score(self):
        # basic sanity-check:
        # count(d | c) = 1
        # *count(d | c) = 2
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 8
        self.score_assertions(0.25)

    @unittest.skip
    def test_entropy_perplexity(self):
        # Unlike MLE this should be able to handle completely novel ngrams
        test_corp = "ac-dc"
        # Ngram = score; log score
        # <s>, a    = 0.(2); -2.1699
        # a, c      = 0.(1); -3.1699
        # c, -      = 0.125; -3.0
        # -, d      = 0.1;  -3.3219
        # d, c      = 0.(1); -3.1699
        # c, </s>   = 0.125; -3.0
        # Total Log Score: -17.8317
        expected_H = 2.972
        expected_perplexity = 7.846
        self.entropy_perp_assertions(expected_H, expected_perplexity)
