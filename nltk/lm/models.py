# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2016 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals, division

from nltk import compat

from nltk.lm.api import LanguageModel, mask_oov_args


@compat.python_2_unicode_compatible
class MLE(LanguageModel):
    """Class for providing MLE ngram model scores.

    Inherits initialization from BaseNgramModel.
    """

    @mask_oov_args
    def score(self, word, context=None):
        """Returns the MLE score for a word given a context.

        Args:
        - word is expcected to be a string
        - context is expected to be something reasonably convertible to a tuple
        """
        counts = self.context_counts(context)
        return counts.freq(word)


@compat.python_2_unicode_compatible
class Lidstone(LanguageModel):
    """Provides Lidstone-smoothed scores.

    In addition to initialization arguments from BaseNgramModel also requires
    a number by which to increase the counts, gamma.
    """

    def __init__(self, gamma, *args, **kwargs):
        super(Lidstone, self).__init__(*args, **kwargs)
        self.gamma = gamma

    @mask_oov_args
    def score(self, word, context=None):
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
