# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2016 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals, division
from math import log

from nltk import compat


NEG_INF = float("-inf")


@compat.python_2_unicode_compatible
class BaseNgramModel(object):
    """An example of how to consume NgramCounter to create a language model.

    This class isn't intended to be used directly, folks should inherit from it
    when writing their own ngram models.
    """

    def __init__(self, ngram_counter):

        self.ngram_counter = ngram_counter
        # for convenient access save top-most ngram order ConditionalFreqDist
        self.ngrams = ngram_counter.ngrams[ngram_counter.order]
        self._ngrams = ngram_counter.ngrams
        self._order = ngram_counter.order

        self._check_against_vocab = self.ngram_counter.check_against_vocab

    def check_context(self, context):
        """Makes sure context not longer than model's ngram order and is a tuple."""
        if len(context) >= self._order:
            raise ValueError("Context is too long for this ngram order: {0}".format(context))
        # ensures the context argument is a tuple
        return tuple(context)

    def score(self, word, context):
        """
        This is a dummy implementation. Child classes should define their own
        implementations.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: sequence[str]
        :rtype: float
        """
        raise NotImplementedError()

    def logscore(self, word, context):
        """
        Evaluate the log probability of this word in this context.

        This implementation actually works, child classes don't have to
        redefine it.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: Tuple[str]
        """
        score = self.score(word, context)
        if score == 0.0:
            return NEG_INF
        return log(score, 2)

    def entropy(self, text):
        """
        Calculate the approximate cross-entropy of the n-gram model for a
        given evaluation text.
        This is the average log probability of each word in the text.

        :param text: words to use for evaluation
        :type text: Iterable[str]
        """

        normed_text = (self._check_against_vocab(word) for word in text)
        H = 0.0     # entropy is conventionally denoted by "H"
        processed_ngrams = 0
        for ngram in self.ngram_counter.to_ngrams(normed_text):
            context, word = tuple(ngram[:-1]), ngram[-1]
            H += self.logscore(word, context)
            processed_ngrams += 1
        return - (H / processed_ngrams)

    def perplexity(self, text):
        """
        Calculates the perplexity of the given text.
        This is simply 2 ** cross-entropy for the text.

        :param text: words to calculate perplexity of
        :type text: Iterable[str]
        """

        return pow(2.0, self.entropy(text))
