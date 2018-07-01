"""Smoothing algorithms for language modeling."""

from nltk.lm.api import Smoothing


class WittenBell(Smoothing):
    """Witten-Bell smoothing."""

    def alpha_gamma(self, word, context):
        gamma = self.gamma(context)
        return (1 - gamma) * self.alpha(word, context), gamma

    def unigram_score(self, word):
        return self.counts.unigrams.freq(word)

    def alpha(self, word, context):
        return self.counts[context].freq(word)

    def gamma(self, context):
        n_plus = sum(1 for c in self.counts[context].values() if c > 0)
        return n_plus / (n_plus + self.counts[len(context) + 1].N())


class KneserNey(Smoothing):
    def __init__(self, *args, discount=0.1, **kwargs):
        super().__init__(*args, *kwargs)
        self.discount = discount

    def unigram_score(self, word):
        return 1. / len(self.vocab)

    def alpha_gamma(self, word, context):
        prefix_counts = self.counts[context]
        return (self.alpha(word, prefix_counts), self.gamma(prefix_counts))

    def alpha(self, word, prefix_counts):
        return max(prefix_counts[word] - self.discount, 0.0) / prefix_counts.N()

    def gamma(self, prefix_counts):
        return self.discount * len(prefix_counts) / prefix_counts.N()
