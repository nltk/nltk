# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2016 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals, division
from math import log
from functools import wraps
import random

from nltk import compat
from nltk.model.util import NEG_INF


def check_args(score_func):
    """Decorator that checks arguments for ngram model score methods."""
    @wraps(score_func)
    def checker(self, word, context=None):
        word_chk = self.mask_oov(word)

        if context is not None:
            if len(context) >= self.order:
                raise ValueError("Context is too long "
                                 "for this ngram order: {0}".format(context))
            context = tuple(map(self.mask_oov, context))

        return score_func(self, word_chk, context)

    return checker


@compat.python_2_unicode_compatible
class BaseNgramModel(object):
    """An example of how to consume NgramCounter to create a language model.

    This class isn't intended to be used directly, folks should inherit from it
    when writing their own ngram models.
    """

    def __init__(self, ngram_counter):

        self.ngram_counter = ngram_counter
        # for convenient access save top-most ngram order ConditionalFreqDist
        self.ngrams = ngram_counter[ngram_counter.order]
        self._ngrams = ngram_counter._ngram_orders

        self.mask_oov = self.ngram_counter.vocabulary.mask_oov

    @property
    def order(self):
        """Provide convenient access to NgramCounter.order."""
        return self.ngram_counter.order

    @check_args
    def score(self, word, context=None):
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

    def context_counts(self, context_checked):
        """Helper method for retrieving counts for a given context.

        Assumes context has been checked and oov words in it masked.
        """
        if context_checked:
            order = len(context_checked) + 1
            return self.ngram_counter[order][context_checked]

        return self.ngram_counter.unigrams

    def logscore(self, word, context=None):
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
        return self._log_base2(score)

    def _log_base2(self, score):
        """Convenience function for computing logarithms with base 2"""
        if score == 0.0:
            return NEG_INF
        return log(score, 2)

    def entropy(self, text_ngrams):
        """
        Calculate the approximate cross-entropy of the n-gram model for a
        given evaluation text.
        This is the average log probability of each word in the text.

        :param text: words to use for evaluation
        :type text: Iterable[str]
        """

        H = 0.0     # entropy is conventionally denoted by "H"
        for ngram in text_ngrams:
            if len(ngram) == 1:
                context, word = None, ngram[0]
            else:
                context, word = ngram[:-1], ngram[-1]
            score = self.score(word, context)
            H -= score * self._log_base2(score)
        return H

    def perplexity(self, text_ngrams):
        """
        Calculates the perplexity of the given text.
        This is simply 2 ** cross-entropy for the text.

        :param text: words to calculate perplexity of
        :type text: Iterable[str]
        """

        return pow(2.0, self.entropy(text_ngrams))

    def generate_one(self, context=None):
        """Generate one word given some context."""
        samples = self.context_counts(context)
        if not samples:
            smaller_context = context[1:] if len(context) > 1 else None
            return self.generate_one(smaller_context)

        rand = random.random()
        scores = list(self.score(w, context) for w in samples)
        for word, score in zip(samples, scores):
            rand -= score
            if rand <= 0:
                return word

    def generate(self, num_words, seed=()):
        """Generate num_words with optional seed provided.

        This essentially wraps the generate_one method to produce sequences.
        """
        text = list(seed) if seed else [self.generate_one()]
        while len(text) < num_words:
            index = -self.order if len(text) >= self.order else len(text)
            relevant_context = tuple(text)[:index]
            next_word = self.generate_one(relevant_context)
            text.append(next_word)
        return text
