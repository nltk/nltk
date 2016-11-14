# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2016 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals, division

from nltk import compat

from nltk.model import BaseNgramModel, check_args


@compat.python_2_unicode_compatible
class MLENgramModel(BaseNgramModel):
    """Class for providing MLE ngram model scores.

    Inherits initialization from BaseNgramModel.
    """
    @check_args
    def score(self, word, context=None):
        """Returns the MLE score for a word given a context.

        Args:
        - word is expcected to be a string
        - context is expected to be something reasonably convertible to a tuple
        """
        counts = self.context_counts(context)
        return counts.freq(word)


@compat.python_2_unicode_compatible
class LidstoneNgramModel(BaseNgramModel):
    """Provides Lidstone-smoothed scores.

    In addition to initialization arguments from BaseNgramModel also requires
    a number by which to increase the counts, gamma.
    """

    def __init__(self, gamma, *args):
        super(LidstoneNgramModel, self).__init__(*args)
        self.gamma = gamma
        # This gets added to the denominator to normalize the effect of gamma
        self.gamma_norm = len(self.ngram_counter.vocabulary) * gamma

    @check_args
    def score(self, word, context=None):
        counts = self.context_counts(context)
        word_count = counts[word]
        norm_count = counts.N()
        return (word_count + self.gamma) / (norm_count + self.gamma_norm)


@compat.python_2_unicode_compatible
class LaplaceNgramModel(LidstoneNgramModel):
    """Implements Laplace (add one) smoothing.

    Initialization identical to BaseNgramModel because gamma is always 1.
    """

    def __init__(self, *args):
        super(LaplaceNgramModel, self).__init__(1, *args)
