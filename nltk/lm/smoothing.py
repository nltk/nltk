# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2020 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
#         Manu Joseph <manujosephv@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""Smoothing algorithms for language modeling.

According to Chen & Goodman 1995 these should work with both Backoff and
Interpolation.
"""

from nltk.lm.api import Smoothing
from nltk import FreqDist, ConditionalFreqDist

def _count_non_zero_vals(distribution):
    if isinstance(distribution, FreqDist):
        return sum(1.0 for c in distribution.values() if c > 0)
    elif isinstance(distribution, ConditionalFreqDist):
        return sum(
            1.0 for c in distribution.keys() if sum(distribution[c].values()) > 0
        )
    else:
        raise NotImplementedError(
            "`distribution` should either be FreqDist or ConditionalFreqDist, but got {} instead.".format(
                type(distribution)
            )
        )


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
        # return (self.counts[word] + 1) / (self.counts[1].N() + len(self.counts[1]))

class KneserNey(Smoothing):
    """Kneser-Ney Smoothing."""

    def __init__(self, vocabulary, counter, discount=0.1, **kwargs):
        super().__init__(vocabulary, counter, **kwargs)
        self.discount = discount
        # Useful for order-level discounting or weight factors
        self._recursion_level = None
        # The first call would be top level.
        self._is_top_recursion = True

    def unigram_score(self, word):
        continuation_count, unique_continuation_count = self.continuation_counts(
            (word,)
        )
        return continuation_count / unique_continuation_count

    def alpha_gamma(self, word, context):
        if self._is_top_recursion:
            prefix_counts = self.counts[context]
            prefix_total_ngrams = prefix_counts.N()
            alpha = max(prefix_counts[word] - self.discount, 0.0) / prefix_total_ngrams
            gamma = (
                self.discount
                * _count_non_zero_vals(prefix_counts)
                / prefix_total_ngrams
            )
        else:
            prefix_counts = self.counts[context]
            prefix_total_ngrams = prefix_counts.N()
            continuation_count, unique_continuation_count = self.continuation_counts(
                context + (word,)
            )
            alpha = (
                max(continuation_count - self.discount, 0.0) / unique_continuation_count
            )
            gamma = (
                self.discount
                * _count_non_zero_vals(prefix_counts)
                / unique_continuation_count
            )
        return alpha, gamma

    def continuation_counts(self, context):
        key_len = len(context) + 1
        continuation_keys = []
        unique_continuation_keys = []
        if len(context) == 1:
            key, value = None, context[-1]
            for word in self.counts[2].keys():
                unique_continuation_keys += [
                    word + (sub_word,) for sub_word in self.counts[2][word]
                ]
                if context[-1] in self.counts[2][word].keys():
                    continuation_keys.append(word + (value,))
        else:
            key, value = context[:-1], context[-1]
            for ngram in self.counts[key_len].keys():
                is_key = ngram[1:] == key
                is_value = value in self.counts[key_len][ngram].keys()
                if is_key:
                    unique_continuation_keys += [
                        ngram + (word,) for word in self.counts[key_len][ngram].keys()
                    ]
                    if is_value:
                        continuation_keys.append(ngram + (value,))
        continuation_count = len(set(continuation_keys))
        unique_continuation_count = len(set(unique_continuation_keys))
        return (continuation_count, unique_continuation_count)
