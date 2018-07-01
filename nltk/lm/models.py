# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2016 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals, division

from nltk import compat
from nltk.lm.api import LanguageModel


@compat.python_2_unicode_compatible
class MLE(LanguageModel):
    """Class for providing MLE ngram model scores.

    Inherits initialization from BaseNgramModel.
    """

    def unmasked_score(self, word, context=None):
        """Returns the MLE score for a word given a context.

        Args:
        - word is expcected to be a string
        - context is expected to be something reasonably convertible to a tuple
        """
        return self.context_counts(context).freq(word)


@compat.python_2_unicode_compatible
class Lidstone(LanguageModel):
    """Provides Lidstone-smoothed scores.

    In addition to initialization arguments from BaseNgramModel also requires
    a number by which to increase the counts, gamma.
    """

    def __init__(self, gamma, *args, **kwargs):
        super(Lidstone, self).__init__(*args, **kwargs)
        self.gamma = gamma

    def unmasked_score(self, word, context=None):
        """Add-one smoothing: Lidstone or Laplace.

        To see what kind, look at `gamma` attribute on the class.

        """
        counts = self.context_counts(context)
        word_count = counts[word]
        norm_count = counts.N()
        return (word_count + self.gamma) / (norm_count + len(self.vocab) * self.gamma)


@compat.python_2_unicode_compatible
class Laplace(Lidstone):
    """Implements Laplace (add one) smoothing.

    Initialization identical to BaseNgramModel because gamma is always 1.
    """

    def __init__(self, *args, **kwargs):
        super(Laplace, self).__init__(1, *args, **kwargs)


class InterpolatedLanguageModel(LanguageModel):
    pass


class WittenBell(InterpolatedLanguageModel):
    """Witten-Bell smoothing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # in line below, order argument to MLE doesn't matter
        self.mle = MLE(1, vocabulary=self.vocab, counter=self.counts)

    def unmasked_score(self, word, context=None):
        if not context:
            return self.mle.unmasked_score(word)
        gamma = self.gamma(context)
        return ((1 - gamma) * self.mle.unmasked_score(word, context)
                + gamma * self.unmasked_score(word, context[1:]))

    def gamma(self, context):
        n_plus = sum(1 for c in self.counts[context].values() if c > 0)
        return n_plus / (n_plus + self.counts[len(context) + 1].N())
