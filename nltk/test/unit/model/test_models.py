# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import division
import unittest
import math

from nltk.model import (build_vocabulary,
                        count_ngrams,
                        NgramModelVocabulary,
                        NgramCounter,
                        BaseNgramModel,
                        MLENgramModel,
                        LidstoneNgramModel,
                        LaplaceNgramModel)
from nltk.model.util import NEG_INF, default_ngrams
from nltk.model.testutil import NgramCounterSetUpMixin

_default_bigrams = default_ngrams(2, only_ngrams=True)


class NgramModelTestBase(unittest.TestCase, NgramCounterSetUpMixin):
    """Base test class for testing ngram model classes"""

    @classmethod
    def setUpClass(cls):
        # The base vocabulary contains 5 items: abcd and UNK
        cls.vocab = NgramModelVocabulary(["a", "b", "c", "d", "z"], unk_cutoff=1)
        # NgramCounter.vocabulary contains 7 items (+2 for padding symbols)
        training_text = ['abcd', 'egadbe']
        cls.bigram_counter = cls.setUpNgramCounter(2, training_text)
        cls.trigram_counter = cls.setUpNgramCounter(3, training_text)

    def total_vocab_score(self, context):
        """Sums up scores for the whole vocabulary given some context.

        Used to make sure they sum to 1.
        Note that we *must* loop over the counter's vocabulary so as to include
        padding symbols.
        """
        return sum(self.model.score(w, context) for w in self.vocab)


class BaseNgramModelTests(NgramModelTestBase):
    """unit tests for BaseNgramModel class"""

    def setUp(self):
        self.model = BaseNgramModel(self.bigram_counter)

    def test_context_counts(self):
        with self.assertRaises(ValueError):
            self.model.context_counts(['a', 'b'])

    def test_score(self):
        with self.assertRaises(NotImplementedError):
            self.model.score("d", ["c"])


class ScoreTestHelper(object):
    """Shared tests and helper code specifically for bigram models."""

    def assertScoreEqual(self, expected_score, word, context):
        """Helper function for testing an ngram model's score method."""
        got_score = self.model.score(word, context=context)

        self.assertAlmostEqual(expected_score, got_score, places=4)

    def assertUnigramScoreEqual(self, expected_score, word="d"):
        self.assertScoreEqual(expected_score, word, context=None)

    def assertEntropyPerplexityEqual(self, H, perplexity,
                                     corpus="ac-dc",
                                     ngram_gen=True):
        """Helper function for testing entropy/perplexity."""
        if ngram_gen:
            got_entropy = self.model.entropy(_default_bigrams(corpus))
            got_perplexity = self.model.perplexity(_default_bigrams(corpus))
        else:
            got_entropy = self.model.entropy(corpus)
            got_perplexity = self.model.perplexity(corpus)
        # We have to be able to deal with NaNs that occur in some cases
        if math.isnan(H) and math.isnan(perplexity):
            self.assertTrue(math.isnan(got_entropy))
            self.assertTrue(math.isnan(got_perplexity))
        else:
            self.assertAlmostEqual(H, got_entropy, places=4)
            self.assertAlmostEqual(perplexity, got_perplexity, places=4)


class BigramModelMixin(ScoreTestHelper):
    """docstring for BigramModelMixin"""

    def test_score_context_too_long(self):
        with self.assertRaises(ValueError) as exc_info:
            self.model.score('d', ('a', 'b'))

    def test_scores_sum_to_1(self):
        # Include some unseen contexts to test
        contexts = (('a',), ('c',), (u'<s>',), ('b',), (u'<UNK>',), ('d',),
                    ('e',), ('r'), ('w',))
        # Laplace (like Lidstone) smoothing can handle contexts unseen during training
        for context in contexts:
            self.assertAlmostEqual(self.total_vocab_score(context), 1)

    def assertScoreEqual(self, expected_score, word="d", context=("c",)):
        super(BigramModelMixin, self).assertScoreEqual(expected_score, word, context)


class TrigramModelMixin(ScoreTestHelper):
    """Tests for trigram models."""

    def assertScoreEqual(self, expected_score, word="d", context=("b", "c")):
        super(TrigramModelMixin, self).assertScoreEqual(expected_score, word, context)


class MleBigramModelTests(NgramModelTestBase, BigramModelMixin):
    """unit tests for MLENgramModel class"""

    def setUp(self):
        self.model = MLENgramModel(self.bigram_counter)

    def test_unigram_score(self):
        # total number of tokens is 14, of which "a" occured 2 times
        self.assertUnigramScoreEqual(2.0 / 14, "a")
        # in vocabulary but unseen
        self.assertUnigramScoreEqual(0, "z")
        # out of vocabulary should use "UNK" score
        self.assertUnigramScoreEqual(3.0 / 14, "y")

    def test_score(self):
        self.assertScoreEqual(1)

    def test_score_unseen(self):
        # Unseen ngrams should yield 0
        score_unseen = self.model.score("d", ["e"])

        self.assertEqual(score_unseen, 0)

    def test_logscore_zero_score(self):
        # logscore of unseen ngrams should be -inf
        logscore = self.model.logscore("d", ["e"])

        self.assertEqual(logscore, NEG_INF)

    def test_entropy_perplexity_seen(self):
        # ngrams seen during training
        trained = "abrad"
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

        self.assertEntropyPerplexityEqual(H, perplexity, corpus=trained)

    def test_entropy_perplexity_unseen(self):
        # In MLE, even one unseen ngram should turn entropy and perplexity into NaN
        untrained = "acd"
        H = perplexity = float("nan")

        self.assertEntropyPerplexityEqual(H, perplexity, corpus=untrained)

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

        corpus = [("<s>",), ("a",), ("c",), ("-",),
                  ("d",), ("c",), ("</s>",)]

        self.assertEntropyPerplexityEqual(H, perplexity, corpus=corpus,
                                          ngram_gen=False)


class MleTrigramModelTests(NgramModelTestBase, TrigramModelMixin):
    """MLE trigram model tests"""

    def setUp(self):
        self.model = MLENgramModel(self.trigram_counter)

    def test_unigram_score(self):
        # total number of tokens is 18, of which "a" occured 2 times
        self.assertUnigramScoreEqual(2.0 / 18, "a")
        # in vocabulary but unseen
        self.assertUnigramScoreEqual(0, "z")
        # out of vocabulary should use "UNK" score
        self.assertUnigramScoreEqual(3.0 / 18, "y")

    def test_score(self):
        # count(d | b, c) = 1
        # count(b, c) = 1
        self.assertScoreEqual(1)

    def test_bigram_score(self):
        # count(d | c) = 1
        # count(c) = 1
        self.assertScoreEqual(1, context=("c",))


class LidstoneBigramModelTests(NgramModelTestBase, BigramModelMixin):
    """unit tests for LidstoneNgramModel class"""

    def setUp(self):
        self.model = LidstoneNgramModel(0.1, self.bigram_counter)

    def test_gamma_and_gamma_norm(self):
        self.assertEqual(0.1, self.model.gamma)
        # There are 8 items in the vocabulary, so we expect gamma norm to be 0.8
        # Due to floating point funkyness in Python, we use float assertion here
        self.assertAlmostEqual(0.8, self.model.gamma_norm)

    def test_score(self):
        # count(d | c) = 1
        # *count(d | c) = 1.1
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 1.8
        self.assertScoreEqual(0.6111)

    def test_unigram_score(self):
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 0.8 = 14.8
        # count("a") = 2
        # *count("a") = 2.1
        self.assertUnigramScoreEqual(2.1 / 14.8, "a")
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 0.1
        self.assertUnigramScoreEqual(0.1 / 14.8, "z")
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 3.1
        self.assertUnigramScoreEqual(3.1 / 14.8, "y")

    def test_entropy_perplexity(self):
        # Unlike MLE this should be able to handle completely novel ngrams
        # Ngram = score, log score, product
        # <s>, a    = 0.3929, -1.3479, -0.5295
        # a, c      = 0.0357, -4.8074, -0.1717
        # c, -      = 0.0556, -4.1699, -0.2317
        # -, d      = 0.0263,  -5.2479, -0.1381
        # d, c      = 0.0357, -4.8074, -0.1717
        # c, </s>   = 0.0556, -4.1699, -0.2317
        # Total product: -1.4744
        H = 1.4744
        perplexity = 2.7786
        self.assertEntropyPerplexityEqual(H, perplexity)


class LidstoneTrigramModelTests(NgramModelTestBase, TrigramModelMixin):

    def setUp(self):
        self.model = LidstoneNgramModel(0.1, self.trigram_counter)

    def test_score(self):
        # Logic behind this is the same as for bigram model
        self.assertScoreEqual(0.6111)
        # if we choose a word that hasn't appeared after (b, c)
        self.assertScoreEqual(0.1 / 1.8, word="e")

    def test_bigram_score(self):
        # Logic behind this is the same as for bigram model
        self.assertScoreEqual(0.6111, context=("c",))
        # if we choose a word that hasn't appeared after (b, c)
        self.assertScoreEqual(0.1 / 1.8, word="e", context=("c",))


class LaplaceBigramModelTests(NgramModelTestBase, BigramModelMixin):
    """unit tests for LaplaceNgramModel class"""

    def setUp(self):
        self.model = LaplaceNgramModel(self.bigram_counter)

    def test_gamma(self):
        # Make sure the gamma is set to 1
        self.assertEqual(1, self.model.gamma)
        # Laplace Gamma norm is just the vocabulary size
        self.assertEqual(8, self.model.gamma_norm)

    def test_score(self):
        # basic sanity-check:
        # count(d | c) = 1
        # *count(d | c) = 2
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 9
        self.assertScoreEqual(0.2222)

    def test_unigram_score(self):
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 8 = 22
        # count("a") = 2
        # *count("a") = 3
        self.assertUnigramScoreEqual(3.0 / 22, "a")
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 1
        self.assertUnigramScoreEqual(1.0 / 22, "z")
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 4
        self.assertUnigramScoreEqual(4.0 / 22, "y")

    def test_entropy_perplexity(self):
        # Unlike MLE this should be able to handle completely novel ngrams
        # Ngram = score, log score, product
        # <s>, a    = 0.(2), -2.1699, -0.4339
        # a, c      = 0.(1), -3.1699, -0.3169
        # c, -      = 0.125, -3.0, -0.375
        # -, d      = 0.1,  -3.3219, -0.3321
        # d, c      = 0.(1) -3.1699, -0.3169
        # c, </s>   = 0.125, -3.0, -0.375
        # Total product: -2.1498
        H = 2.1477
        perplexity = 4.4312
        self.assertEntropyPerplexityEqual(H, perplexity)


class NgramModelTextGenerationTests(NgramModelTestBase):
    """Using MLE estimator, generate some text."""

    def setUp(self):
        self.model = MLENgramModel(self.trigram_counter)

    def test_generate_one_no_context(self):
        generated = self.model.generate_one()
        self.assertIn(generated, self.model.ngram_counter.unigrams)

    def test_generate_one_small_context(self):
        context = ("c",)
        generated = self.model.generate_one(context=context)

        self.assertIn(generated, self.model.ngram_counter[2][context])

    def test_generate_one_normal_context(self):
        context = ("b", "c")
        generated = self.model.generate_one(context=context)

        self.assertIn(generated, self.model.ngram_counter[3][context])

    def test_generate_one_backoff_to_smaller_context(self):
        context_no_samples = ("a", "c")
        expected_samples = self.model.ngram_counter[2][("c",)]
        generated = self.model.generate_one(context_no_samples)

        self.assertIn(generated, expected_samples)

    def test_generate_one_backoff_to_unigrams(self):
        context_no_samples = ("a", "</s>")
        expected_samples = self.model.ngram_counter.unigrams
        generated = self.model.generate_one(context_no_samples)

        self.assertIn(generated, expected_samples)

    def test_generate_no_seed_unigrams(self):
        generated_text = self.model.generate(5)

        self.assertEqual(5, len(generated_text))
        # With no seed, first item should be one of unigrams
        self.assertIn(generated_text[0], self.model.ngram_counter[1])

    def test_generate_with_bigram_seed(self):
        # seed has to be picked so as to make the test deterministic!
        seed = ("c",)
        seed_continuations = self.model.ngram_counter[2][seed]
        generated_text = self.model.generate(5, seed=seed)

        # seed should be the first item
        self.assertEqual(generated_text[0], seed[0])
        # Second item should depend on seed
        self.assertIn(generated_text[1], seed_continuations)