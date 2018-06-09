"""Smoothing algorithms for language modeling."""

from .models import MleLanguageModel


class WittenBell:
    """Witten-Bell smoothing."""

    def __init__(self, counter, vocabulary, beta_model=MleLanguageModel):
        self.counts = counter
        self.vocab = vocabulary
        self.mle = MleLanguageModel(2)
        self.mle.vocab = vocabulary
        self.mle.counts = counter
        self.beta_model = beta_model(2)
        self.beta_model.vocab = vocabulary
        self.beta_model.counts = counter

    def gamma(self, context):
        n_plus = sum(1 for c in self.counts[context].values() if c > 0)
        return n_plus / (n_plus + self.counts[len(context) + 1].N())

    def alpha(self, word, context):
        return (1 - self.gamma(context)) * self.mle.score(word, context)

    def beta(self, word, context):
        return self.beta_model.score(word, context)

    def recurse(self, context):
        return list(range(len(context)))
