# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""Language Models"""

from nltk.lm.api import LanguageModel, Smoothing
from nltk.lm.smoothing import KneserNey, WittenBell


class MLE(LanguageModel):
    """Class for providing MLE ngram model scores.

    Inherits initialization from BaseNgramModel.
    """

    def unmasked_score(self, word, context=None):
        """Returns the MLE score for a word given a context.

        Args:
        - word is expected to be a string
        - context is expected to be something reasonably convertible to a tuple
        """
        return self.context_counts(context).freq(word)


class Lidstone(LanguageModel):
    """Provides Lidstone-smoothed scores.

    In addition to initialization arguments from BaseNgramModel also requires
    a number by which to increase the counts, gamma.
    """

    def __init__(self, gamma, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gamma = gamma

    def unmasked_score(self, word, context=None):
        """Add-one smoothing: Lidstone or Laplace.

        To see what kind, look at `gamma` attribute on the class.

        """
        counts = self.context_counts(context)
        word_count = counts[word]
        norm_count = counts.N()
        return (word_count + self.gamma) / (norm_count + len(self.vocab) * self.gamma)


class Laplace(Lidstone):
    """Implements Laplace (add one) smoothing.

    Initialization identical to BaseNgramModel because gamma is always 1.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(1, *args, **kwargs)


class InterpolatedLanguageModel(LanguageModel):
    """Logic common to all interpolated language models.

    The idea to abstract this comes from Chen & Goodman 1995.
    Do not instantiate this class directly!
    """

    def __init__(self, smoothing_cls, order, **kwargs):
        assert issubclass(smoothing_cls, Smoothing)
        params = kwargs.pop("params", {})
        super().__init__(order, **kwargs)
        self.estimator = smoothing_cls(self.vocab, self.counts, **params)

    def unmasked_score(self, word, context=None):
        if not context:
            # The base recursion case: no context, we only have a unigram.
            return self.estimator.unigram_score(word)
        if not self.counts[context]:
            # It can also happen that we have no data for this context.
            # In that case we defer to the lower-order ngram.
            # This is the same as setting alpha to 0 and gamma to 1.
            return self.unmasked_score(word, context[1:])
        alpha, gamma = self.estimator.alpha_gamma(word, context)
        return alpha + gamma * self.unmasked_score(word, context[1:])


class WittenBellInterpolated(InterpolatedLanguageModel):
    """Interpolated version of Witten-Bell smoothing."""

    def __init__(self, order, **kwargs):
        super().__init__(WittenBell, order, **kwargs)


class KneserNeyInterpolated(InterpolatedLanguageModel):
    """Interpolated version of Kneser-Ney smoothing."""

    def __init__(self, order, discount=0.1, **kwargs):
        super().__init__(KneserNey, order, params={"discount": discount}, **kwargs)
