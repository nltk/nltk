# -*- coding: utf-8 -*-
# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2019 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""Smoothing algorithms for language modeling.

According to Chen & Goodman 1995 these should work with both Backoff and
Interpolation.
"""

from nltk.lm.api import Smoothing


def _count_non_zero_vals(dictionary):
    return sum(1.0 for c in dictionary.values() if c > 0)


class WittenBell(Smoothing):
    """Witten-Bell smoothing."""

    def __init__(self, vocabulary, counter, discount=0.1, **kwargs):
        super(WittenBell, self).__init__(vocabulary, counter, *kwargs)
        self.counts = counter

    def alpha_gamma(self, word, context):
        gamma = self.gamma(context)
        return (1.0 - gamma) * self.alpha(word, context), gamma

    def unigram_score(self, word):
        return self.counts.unigrams.freq(word)

    def alpha(self, word, context):
        return self.counts[context].freq(word)

    def gamma(self, context):
        n_plus = _count_non_zero_vals(self.counts[context])
        return n_plus / (n_plus + self.counts[len(context) + 1].N())


class KneserNey(Smoothing):
    """Kneser-Ney Smoothing."""

    def __init__(self, vocabulary, counter, discount=0.1, **kwargs):
        super(KneserNey, self).__init__(vocabulary, counter, *kwargs)
        self.discount = discount
        self.vocabulary = vocabulary

    def unigram_score(self, word):
        return 1.0 / len(self.vocabulary)

    def alpha_gamma(self, word, context):
        prefix_counts = self.counts[context]
        return self.alpha(word, prefix_counts), self.gamma(prefix_counts)

    def alpha(self, word, prefix_counts):
        return max(prefix_counts[word] - self.discount, 0.0) / prefix_counts.N()

    def gamma(self, prefix_counts):
        return self.discount * _count_non_zero_vals(prefix_counts) / prefix_counts.N()


class GoodTuring(Smoothing):
    """Good-Turing Smoothing"""
    def __init__(self, vocabulary, counter, **kwargs):
        super(GoodTuring, self).__init__(vocabulary, counter, *kwargs)
        self.counts = counter
        self.vocabulary = vocabulary

    def unigram_score(self, word):
        word_count = self.counts[word]
        count_plus_1 = 0.
        for everyContext in self.counts.keys():
            if len(everyContext.split()) == word_count+1:
                count_plus_1 += 1
        return count_plus_1 / len(self.vocabulary)
