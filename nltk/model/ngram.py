# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2016 NLTK Project
# Authors: Steven Bird <stevenbird1@gmail.com>
#          Daniel Blanchard <dblanchard@ets.org>
#          Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals

from math import log

from nltk.model.api import NgramModelI
from nltk.model.counter import NgramCounter

from nltk import compat


NEG_INF = -1e6


@compat.python_2_unicode_compatible
class MLENgramModel(NgramModelI):
    """An example of how to consume NgramCounter to create a language model.

    Currently untested.
    """

    def __init__(self, highest_order, training_text, unknown_cutoff,
                 **ngram_counter_kwargs):
        self.counter = NgramCounter(highest_order, training_text, unknown_cutoff,
                                    **ngram_counter_kwargs)

        self.ngrams = self.counter.ngrams[self.counter.order]

        self._normalize = self.counter.check_against_vocab

    def score(self, word, context):
        """
        Evaluate the probability of this word in this context using MLE.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: Tuple[str]
        """
        if len(context) > self.counter.order - 1:
            raise ValueError("Context too long for this model!")

        norm_word = self._normalize(word)
        norm_context = tuple(self.normalize_word(word) for word in context)

        mle_score = self.ngrams[norm_context][norm_word]
        if mle_score > 0:
            return mle_score
        return NEG_INF

    def logscore(self, word, context):
        """
        Evaluate the (negative) log probability of this word in this context.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: Tuple[str]
        """
        return -log(self.prob(word, context), 2)

    def entropy(self, text):
        """
        Calculate the approximate cross-entropy of the n-gram model for a
        given evaluation text.
        This is the average log probability of each word in the text.

        :param text: words to use for evaluation
        :type text: Iterable[str]
        """

        H = 0.0     # entropy is conventionally denoted by "H"
        normed_text = (self._normalize(word) for word in text)
        processed_ngrams = 0.0
        for ngram in self.counter.padded_ngrams(normed_text):
            context, word = tuple(ngram[:-1]), ngram[-1]
            H += self.logprob(word, context)
            processed_ngrams += 1.0
        return H / processed_ngrams

    def perplexity(self, text):
        """
        Calculates the perplexity of the given text.
        This is simply 2 ** cross-entropy for the text.

        :param text: words to calculate perplexity of
        :type text: Iterable[str]
        """

        return pow(2.0, self.entropy(text))
