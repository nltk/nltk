# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2020 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
import math
import pytest


from nltk.lm import (
    Vocabulary,
    MLE,
    Lidstone,
    Laplace,
    WittenBellInterpolated,
    KneserNeyInterpolated,
)
from nltk.lm.preprocessing import padded_everygrams



def _prepare_test_data(ngram_order):
    return (
        Vocabulary(["a", "b", "c", "d", "z", "<s>", "</s>"], unk_cutoff=1),
        [
            padded_everygrams(ngram_order, sent)
            for sent in (list("abcd"), list("egadbe"))
        ],
    )


class ParametrizedTests(type):
    """Metaclass for generating parametrized tests."""
    contexts = [
        ("a",),
        ("c",),
        (u"<s>",),
        ("b",),
        (u"<UNK>",),
        ("d",),
        ("e",),
        ("r",),
        ("w",),
    ]

    def __new__(cls, name, bases, dct):
        scores = dct.get("score_tests", [])
        for i, (word, context, expected_score) in enumerate(scores):
            dct["test_score_{}".format(i)] = cls.add_score_test(
                word, context, expected_score
            )
        return super().__new__(cls, name, bases, dct)

    @pytest.mark.parametrize("context", contexts)
    def test_sum_to_1(self, context):
        message = "The context is {}".format(context)
        s = sum(self.model.score(w, context) for w in self.model.vocab)
        assert pytest.approx(s, 1e-7) == 1.0, message

    @classmethod
    def add_score_test(self, word, context, expected_score):
        message = "word='{}', context={}".format(word, context)

        def test_method(self):
            score = self.model.score(word, context)
            assert pytest.approx(score, 1e-4) == expected_score, message

        return test_method


class TestMleBigram(metaclass=ParametrizedTests):
    """Unit tests for MLE ngram model."""

    score_tests = [
        ("d", ["c"], 1),
        # Unseen ngrams should yield 0
        ("d", ["e"], 0),
        # Unigrams should also be 0
        ("z", None, 0),
        # N unigrams = 14
        # count('a') = 2
        ("a", None, 2.0 / 14),
        # count('y') = 3
        ("y", None, 3.0 / 14),
    ]

    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(2)
        self.model = MLE(2, vocabulary=vocab)
        self.model.fit(training_text)

    def test_logscore_zero_score(self):
        # logscore of unseen ngrams should be -inf
        logscore = self.model.logscore("d", ["e"])
        assert math.isinf(logscore)

    def test_entropy_perplexity_seen(self):
        # ngrams seen during training
        trained = [
            ("<s>", "a"),
            ("a", "b"),
            ("b", "<UNK>"),
            ("<UNK>", "a"),
            ("a", "d"),
            ("d", "</s>"),
        ]
        # Ngram = Log score
        # <s>, a    = -1
        # a, b      = -1
        # b, UNK    = -1
        # UNK, a    = -1.585
        # a, d      = -1
        # d, </s>   = -1
        # TOTAL logscores   = -6.585
        # - AVG logscores   = 1.0975
        H = 1.0975
        perplexity = 2.1398
        assert pytest.approx(self.model.entropy(trained), 1e-4) == H
        assert pytest.approx(self.model.perplexity(trained), 1e-4) == perplexity

    def test_entropy_perplexity_unseen(self):
        # In MLE, even one unseen ngram should make entropy and perplexity infinite
        untrained = [("<s>", "a"), ("a", "c"), ("c", "d"), ("d", "</s>")]

        assert math.isinf(self.model.entropy(untrained))
        assert math.isinf(self.model.perplexity(untrained))

    def test_entropy_perplexity_unigrams(self):
        # word = score, log score
        # <s>   = 0.1429, -2.8074
        # a     = 0.1429, -2.8074
        # c     = 0.0714, -3.8073
        # UNK   = 0.2143, -2.2224
        # d     = 0.1429, -2.8074
        # c     = 0.0714, -3.8073
        # </s>  = 0.1429, -2.8074
        # TOTAL logscores = -21.6243
        # - AVG logscores = 3.0095
        H = 3.0095
        perplexity = 8.0529

        text = [("<s>",), ("a",), ("c",), ("-",), ("d",), ("c",), ("</s>",)]

        assert pytest.approx(self.model.entropy(text), 1e-4) == H
        assert pytest.approx(self.model.perplexity(text), 1e-4) == perplexity


class TestMleTrigram(metaclass=ParametrizedTests):
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
        ("y", None, 3.0 / 18),
    ]

    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(3)
        self.model = MLE(3, vocabulary=vocab)
        self.model.fit(training_text)


class TestLidstoneBigram(metaclass=ParametrizedTests):
    """Unit tests for Lidstone class"""

    score_tests = [
        # count(d | c) = 1
        # *count(d | c) = 1.1
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 1.8
        ("d", ["c"], 1.1 / 1.8),
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 0.8 = 14.8
        # count("a") = 2
        # *count("a") = 2.1
        ("a", None, 2.1 / 14.8),
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 0.1
        ("z", None, 0.1 / 14.8),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 3.1
        ("y", None, 3.1 / 14.8),
    ]

    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(2)
        self.model = Lidstone(0.1, 2, vocabulary=vocab)
        self.model.fit(training_text)

    def test_gamma(self):
        assert 0.1 == self.model.gamma

    def test_entropy_perplexity(self):
        text = [
            ("<s>", "a"),
            ("a", "c"),
            ("c", "<UNK>"),
            ("<UNK>", "d"),
            ("d", "c"),
            ("c", "</s>"),
        ]
        # Unlike MLE this should be able to handle completely novel ngrams
        # Ngram = score, log score
        # <s>, a    = 0.3929, -1.3479
        # a, c      = 0.0357, -4.8074
        # c, UNK    = 0.0(5), -4.1699
        # UNK, d    = 0.0263,  -5.2479
        # d, c      = 0.0357, -4.8074
        # c, </s>   = 0.0(5), -4.1699
        # TOTAL logscore: −24.5504
        # - AVG logscore: 4.0917
        H = 4.0917
        perplexity = 17.0504
        assert pytest.approx(self.model.entropy(text), 1e-4) == H
        assert pytest.approx(self.model.perplexity(text), 1e-4) == perplexity


class TestLidstoneTrigram(metaclass=ParametrizedTests):
    score_tests = [
        # Logic behind this is the same as for bigram model
        ("d", ["c"], 1.1 / 1.8),
        # if we choose a word that hasn't appeared after (b, c)
        ("e", ["c"], 0.1 / 1.8),
        # Trigram score now
        ("d", ["b", "c"], 1.1 / 1.8),
        ("e", ["b", "c"], 0.1 / 1.8),
    ]

    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(3)
        self.model = Lidstone(0.1, 3, vocabulary=vocab)
        self.model.fit(training_text)


class TestLaplaceBigram(metaclass=ParametrizedTests):
    """Unit tests for Laplace class"""

    score_tests = [
        # basic sanity-check:
        # count(d | c) = 1
        # *count(d | c) = 2
        # Count(w | c for w in vocab) = 1
        # *Count(w | c for w in vocab) = 9
        ("d", ["c"], 2.0 / 9),
        # Total unigrams: 14
        # Vocab size: 8
        # Denominator: 14 + 8 = 22
        # count("a") = 2
        # *count("a") = 3
        ("a", None, 3.0 / 22),
        # in vocabulary but unseen
        # count("z") = 0
        # *count("z") = 1
        ("z", None, 1.0 / 22),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        # *count("<UNK>") = 4
        ("y", None, 4.0 / 22),
    ]

    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(2)
        self.model = Laplace(2, vocabulary=vocab)
        self.model.fit(training_text)

    def test_gamma(self):
        # Make sure the gamma is set to 1
        assert 1 == self.model.gamma

    def test_entropy_perplexity(self):
        text = [
            ("<s>", "a"),
            ("a", "c"),
            ("c", "<UNK>"),
            ("<UNK>", "d"),
            ("d", "c"),
            ("c", "</s>"),
        ]
        # Unlike MLE this should be able to handle completely novel ngrams
        # Ngram = score, log score
        # <s>, a    = 0.2, -2.3219
        # a, c      = 0.1, -3.3219
        # c, UNK    = 0.(1), -3.1699
        # UNK, d    = 0.(09), 3.4594
        # d, c      = 0.1 -3.3219
        # c, </s>   = 0.(1), -3.1699
        # Total logscores: −18.7651
        # - AVG logscores: 3.1275
        H = 3.1275
        perplexity = 8.7393
        assert pytest.approx(self.model.entropy(text), 1e-4) == H
        assert pytest.approx(self.model.perplexity(text), 1e-4) == perplexity


class TestWittenBellInterpolatedTrigram(metaclass=ParametrizedTests):
    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(3)
        self.model = WittenBellInterpolated(3, vocabulary=vocab)
        self.model.fit(training_text)

    score_tests = [
        # For unigram scores by default revert to regular MLE
        # Total unigrams: 18
        # Vocab Size = 7
        # count('c'): 1
        ("c", None, 1.0 / 18),
        # in vocabulary but unseen
        # count("z") = 0
        ("z", None, 0 / 18),
        # out of vocabulary should use "UNK" score
        # count("<UNK>") = 3
        ("y", None, 3.0 / 18),
        # 2 words follow b and b occured a total of 2 times
        # gamma(['b']) = 2/(2+2) = 0.5
        # mle.score('c', ['b']) = 0.5
        # mle('c') = 1/18 = 0.055
        # (1 - gamma) * mle + gamma * mle('c') ~= 0.27 + 0.055
        ("c", ["b"], (1 - 0.5) * 0.5 + 0.5 * 1 / 18),
        # building on that, let's try 'a b c' as the trigram
        # 1 word follows 'a b' and 'a b' occured 1 time
        # gamma(['a', 'b']) = 1/(1+1) = 0.5
        # mle("c", ["a", "b"]) = 1
        ("c", ["a", "b"], (1 - 0.5) + 0.5 * ((1 - 0.5) * 0.5 + 0.5 * 1 / 18)),
        # The ngram 'z b c' was not seen, so we should simply revert to
        # the score of the ngram 'b c'. See issue #2332.
        ("c", ["z", "b"], ((1 - 0.5) * 0.5 + 0.5 * 1 / 18)),
    ]


class TestKneserNeyInterpolatedTrigram(metaclass=ParametrizedTests):
    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(3)
        self.model = KneserNeyInterpolated(3, vocabulary=vocab)
        self.model.fit(training_text)

    score_tests = [
        # For unigram scores revert to uniform
        # Vocab size: 8
        # count('c'): 1
        ("c", None, 1.0 / 8),
        # in vocabulary but unseen, still uses uniform
        ("z", None, 1 / 8),
        # out of vocabulary should use "UNK" score, i.e. again uniform
        ("y", None, 1.0 / 8),
        # alpha = count('bc') - discount = 1 - 0.1 = 0.9
        # gamma(['b']) = discount * number of unique words that follow ['b'] = 0.1 * 2
        # normalizer = total number of bigrams with this context = 2
        # the final should be: (alpha + gamma * unigram_score("c"))
        ("c", ["b"], (0.9 + 0.2 * (1 / 8)) / 2),
        # building on that, let's try 'a b c' as the trigram
        # alpha = count('abc') - discount = 1 - 0.1 = 0.9
        # gamma(['a', 'b']) = 0.1 * 1
        # normalizer = total number of trigrams with prefix "ab" = 1 => we can ignore it!
        ("c", ["a", "b"], 0.9 + 0.1 * ((0.9 + 0.2 * (1 / 8)) / 2)),
        # The ngram 'z b c' was not seen, so we should simply revert to
        # the score of the ngram 'b c'. See issue #2332.
        ("c", ["z", "b"], ((0.9 + 0.2 * (1 / 8)) / 2)),
    ]


class TestNgramModelTextGeneration:
    """Using MLE model, generate some text."""

    @classmethod
    def setup_method(self):
        vocab, training_text = _prepare_test_data(3)
        self.model = MLE(3, vocabulary=vocab)
        self.model.fit(training_text)

    def test_generate_one_no_context(self):
        assert self.model.generate(random_seed=3) == "<UNK>"

    def test_generate_one_limiting_context(self):
        # We don't need random_seed for contexts with only one continuation
        assert self.model.generate(text_seed=["c"]) == "d"
        assert self.model.generate(text_seed=["b", "c"]) == "d"
        assert self.model.generate(text_seed=["a", "c"]) == "d"

    def test_generate_one_varied_context(self):
        # When context doesn't limit our options enough, seed the random choice
        assert self.model.generate(text_seed=("a", "<s>"), random_seed=2) == "a"

    def test_generate_cycle(self):
        # Add a cycle to the model: bd -> b, db -> d
        more_training_text = [padded_everygrams(self.model.order, list("bdbdbd"))]

        self.model.fit(more_training_text)
        # Test that we can escape the cycle
        assert (
            self.model.generate(7, text_seed=("b", "d"), random_seed=5)
            == ["b", "d", "b", "d", "b", "d", "</s>"]
        )

    def test_generate_with_text_seed(self):
        assert (
            self.model.generate(5, text_seed=("<s>", "e"), random_seed=3)
            == ["<UNK>", "a", "d", "b", "<UNK>"]
        )

    def test_generate_oov_text_seed(self):
        assert (
            self.model.generate(text_seed=("aliens",), random_seed=3)
            == self.model.generate(text_seed=("<UNK>",), random_seed=3)
        )

    def test_generate_None_text_seed(self):
        # should crash with type error when we try to look it up in vocabulary
        with pytest.raises(TypeError):
            self.model.generate(text_seed=(None,))

        # This will work
        assert (
            self.model.generate(text_seed=None, random_seed=3)
            == self.model.generate(random_seed=3)
        )
