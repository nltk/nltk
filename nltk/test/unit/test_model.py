# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import division

import unittest

from nltk.model import build_vocabulary, count_ngrams
from nltk.model.counter import NgramModelVocabulary, EmptyVocabularyError, NgramCounter
from nltk.model.ngram import (BaseNgramModel,
                              MLENgramModel,
                              LidstoneNgramModel,
                              LaplaceNgramModel,
                              NEG_INF)


class NgramCounterTests(unittest.TestCase):
    """Tests NgramCounter class"""

    @classmethod
    def setUpClass(self):
        self.vocab = NgramModelVocabulary(2, "abcdeadbe")

        self.trigram_counter = NgramCounter(3, self.vocab)
        self.trigram_counter.train_counts(['abcd', 'egdbe'])

        self.bigram_counter = NgramCounter(2, self.vocab)
        self.bigram_counter.train_counts(['abcd', 'egdbe'])

    def test_NgramCounter_order_attr(self):
        self.assertEqual(self.trigram_counter.order, 3)

    def test_NgramCounter_breaks_given_invalid_order(self):
        with self.assertRaises(ValueError) as exc_info:
            NgramCounter(0, self.vocab)
        expected_error_msg = "Order of NgramCounter cannot be less than 1. Got: 0"
        self.assertEqual(str(exc_info.exception), expected_error_msg)

    def test_NgramCounter_breaks_given_empty_vocab(self):
        empty_vocab = NgramModelVocabulary(2, "abc")
        empty_counter = NgramCounter(2, empty_vocab, pad_left=False, pad_right=False)

        with self.assertRaises(EmptyVocabularyError) as exc_info:
            empty_counter.train_counts(['ad', 'hominem'])

        self.assertEqual(("Cannot start counting ngrams until "
                          "vocabulary contains more than one item."),
                         str(exc_info.exception))

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


class NgramModelBaseTest(unittest.TestCase):
    """Base test class for testing ngram model classes"""

    @classmethod
    def setUpClass(self):
        # The base vocabulary contains 5 items: abcd and UNK
        self.vocab = NgramModelVocabulary(1, "abcd")
        # NgramCounter.vocabulary contains 7 items (+2 for padding symbols)
        self.counter = NgramCounter(2, self.vocab)
        self.counter.train_counts(['abcd', 'egadbe'])

    def total_vocab_score(self, context):
        """Sums up scores for the whole vocabulary given some context.

        Used to make sure they sum to 1.
        Note that we *must* loop over the counter's vocabulary so as to include
        padding symbols.
        """
        return (sum(self.model.score(w, context) for w in self.counter.vocabulary)
                + self.model.score(self.counter.unk_label, context))


class BaseNgramModelTests(NgramModelBaseTest):
    """unit tests for BaseNgramModel class"""

    def setUp(self):
        self.model = BaseNgramModel(self.counter)

    def test_aliases(self):
        self.assertEqual(self.model._order, 2)
        self.assertEqual(self.model._ngrams, self.counter.ngrams)
        self.assertEqual(self.model._check_against_vocab, self.counter.check_against_vocab)

    def test_context_checker(self):
        ctx_tuple = self.model.check_context(('a',))
        ctx_list = self.model.check_context(['a'])

        self.assertEqual(ctx_list, ctx_tuple)

        with self.assertRaises(ValueError):
            self.model.check_context(['a', 'b'])

        with self.assertRaises(TypeError):
            self.model.check_context(None)

    def test_score(self):
        # should always return 0.5
        # should handle both lists and tuples as context
        score1 = self.model.score("b", ["a"])
        score2 = self.model.score("c", ("a",))
        # Should also handle various empty context
        score3 = self.model.score("c", "")
        score4 = self.model.score("c", [])

        self.assertEqual(score1, 0.5)
        self.assertEqual(score1, score2)
        self.assertEqual(score1, score3)
        self.assertEqual(score1, score4)


class MLENgramModelTests(NgramModelBaseTest):
    """unit tests for MLENgramModel class"""

    def setUp(self):
        self.model = MLENgramModel(self.counter)

    def test_score(self):
        score_ctx_list = self.model.score("d", ["c"])
        score_ctx_tuple = self.model.score("b", ("a",))

        self.assertEqual(score_ctx_list, 1)
        self.assertEqual(score_ctx_tuple, 0.5)

    def test_score_context_too_long(self):
        with self.assertRaises(ValueError) as exc_info:
            self.model.score('d', ('a', 'b'))

    def test_score_unseen(self):
        # Unseen ngrams should yield 0
        score_unseen = self.model.score("d", ["e"])

        self.assertEqual(score_unseen, 0)

    def test_score_sums_to_1(self):
        seen_contexts = (('a',), ('c',), (u'<s>',), ('b',), (u'<UNK>',), ('d',))

        for context in seen_contexts:
            self.assertEqual(self.total_vocab_score(context), 1)

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

    def test_entropy_perplexity_unseen(self):
        # In MLE, even one unseen ngram should turn entropy and perplexity into INF
        unseen_ngram = "acd"

        self.assertEqual(float("inf"), self.model.entropy(unseen_ngram))
        self.assertEqual(float("inf"), self.model.perplexity(unseen_ngram))


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
        expected_score = 0.6471

        got_score_list = self.model.score("d", ["c"])
        got_score_tuple = self.model.score("d", ("c",))

        self.assertAlmostEqual(expected_score, got_score_list, places=4)
        self.assertEqual(got_score_list, got_score_tuple)

    def test_score_context_too_long(self):
        with self.assertRaises(ValueError) as exc_info:
            self.model.score('d', ('a', 'b'))

    def test_scores_sum_to_1(self):
        # Lidstone smoothing can handle contexts unseen during training
        mixed_contexts = (('a',), ('c',), (u'<s>',), ('b',), (u'<UNK>',), ('d',),
                          ('e',), ('r'), ('w',))

        for context in mixed_contexts:
            self.assertAlmostEqual(self.total_vocab_score(context), 1)

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

        self.assertAlmostEqual(expected_H, self.model.entropy(test_corp), places=4)
        self.assertAlmostEqual(expected_perplexity, self.model.perplexity(test_corp), places=4)


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
        expected_score = 0.25

        got_score_list = self.model.score("d", ["c"])
        got_score_tuple = self.model.score("d", ("c",))

        self.assertAlmostEqual(expected_score, got_score_list, places=4)
        self.assertEqual(got_score_list, got_score_tuple)

    def test_score_context_too_long(self):
        with self.assertRaises(ValueError) as exc_info:
            self.model.score('d', ('a', 'b'))

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

        self.assertAlmostEqual(expected_H, self.model.entropy(test_corp), places=4)
        self.assertAlmostEqual(expected_perplexity, self.model.perplexity(test_corp), places=4)

    def test_scores_sum_to_1(self):
        # Laplace (like Lidstone) smoothing can handle contexts unseen during training
        mixed_contexts = (('a',), ('c',), (u'<s>',), ('b',), (u'<UNK>',), ('d',),
                          ('e',), ('r'), ('w',))

        for context in mixed_contexts:
            self.assertAlmostEqual(self.total_vocab_score(context), 1)


class ModelFuncsTests(unittest.TestCase):
    """Tests for module functions.

    They are essentially integration tests.
    """

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

    def test_count_ngrams(self):
        vocab = build_vocabulary(2, 'abcdead')
        counter = count_ngrams(2, vocab, ['abcfdezgadbew'])

        bigrams = counter.ngrams[2]

        self.assertEqual(bigrams[("a",)]['b'], 0)
        self.assertEqual(bigrams[("a",)]['d'], 1)
        self.assertEqual(bigrams[("<s>",)]['a'], 1)

    def test_count_ngrams_multiple_texts(self):
        vocab_text = ("the cow jumped over the blue moon . "
                      "blue river jumped over the rainbow .")
        vocab = build_vocabulary(2, vocab_text.split())

        text1 = ['zabcfdegadbew']
        text2 = ["blue moon".split(), "over the rainbow".split()]
        counter = count_ngrams(2, vocab, text1, text2)

        bigrams = counter.ngrams[2]

        self.assertEqual(bigrams[("blue",)]['river'], 0)
        self.assertEqual(bigrams[("blue",)]['<UNK>'], 1)
        self.assertEqual(bigrams[("over",)]['the'], 1)

    def test_count_ngrams_kwargs(self):
        vocab_text = ("the cow jumped over the blue moon . "
                      "blue river jumped over the rainbow .")
        vocab = build_vocabulary(2, vocab_text.split())

        text = ["blue moon".split(), "over the rainbow".split()]
        counter = count_ngrams(2, vocab, text, left_pad_symbol="TEST")

        self.assertEqual(counter.ngrams[2][("TEST",)]["blue"], 1)

    def test_count_grams_bad_kwarg(self):
        vocab_text = ("the cow jumped over the blue moon . "
                      "blue river jumped over the rainbow .")
        vocab = build_vocabulary(2, vocab_text.split())

        text = ["blue moon".split()]
        with self.assertRaises(TypeError) as exc_info:
            count_ngrams(2, vocab, text, dummy_kwarg="TEST")

        expected_error_msg = "ngrams() got an unexpected keyword argument 'dummy_kwarg'"
        self.assertEqual(expected_error_msg, str(exc_info.exception))
