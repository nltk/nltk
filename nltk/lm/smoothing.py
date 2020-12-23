# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2020 NLTK Project
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

    def __init__(self, vocabulary, counter, **kwargs):
        super().__init__(vocabulary, counter, **kwargs)

    def alpha_gamma(self, word, context):
        alpha = self.counts[context].freq(word)
        gamma = self._gamma(context)
        return (1.0 - gamma) * alpha, gamma

    def _gamma(self, context):
        n_plus = _count_non_zero_vals(self.counts[context])
        return n_plus / (n_plus + self.counts[context].N())

    def unigram_score(self, word):
        return self.counts.unigrams.freq(word)


class KneserNey(Smoothing):
    """Kneser-Ney Smoothing."""

    def __init__(self, vocabulary, counter, discount=0.1, **kwargs):
        super().__init__(vocabulary, counter, **kwargs)
        self.discount = discount

    def unigram_score(self, word):
        return 1.0 / len(self.vocab)

    def alpha_gamma(self, word, context):
        prefix_counts = self.counts[context]
        prefix_total_ngrams = prefix_counts.N()
        alpha = max(prefix_counts[word] - self.discount, 0.0) / prefix_total_ngrams
        gamma = (
            self.discount * _count_non_zero_vals(prefix_counts) / prefix_total_ngrams
        )
        return alpha, gamma
