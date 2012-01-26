# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2012 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
#          Daniel Blanchard <dan.blanchard@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from itertools import chain
from math import log

from nltk.probability import (ConditionalProbDist, ConditionalFreqDist,
                              SimpleGoodTuringProbDist)
from nltk.util import ingrams
from nltk.model.api import ModelI


def _estimator(fdist, bins):
    """
    Default estimator function using a SimpleGoodTuringProbDist.
    """
    # can't be an instance method of NgramModel as they
    # can't be pickled either.
    return SimpleGoodTuringProbDist(fdist)


class NgramModel(ModelI):
    """
    A processing interface for assigning a probability to the next word.
    """

    # add cutoff
    def __init__(self, n, train, estimator=None, *estimator_args, **estimator_kw_args):
        """
        Creates an ngram language model to capture patterns in n consecutive
        words of training text.  An estimator smooths the probabilities derived
        from the text and may allow generation of ngrams not seen during
        training.

            >>> from nltk.corpus import brown
            >>> from nltk.probability import LidstoneProbDist
            >>> estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
            >>> lm = NgramModel(3, brown.words(categories='news'), estimator)
            >>> lm.entropy(['The', 'Fulton', 'County', 'Grand', 'Jury', 'said',
            ... 'Friday', 'an', 'investigation', 'of', "Atlanta's", 'recent',
            ... 'primary', 'election', 'produced', '``', 'no', 'evidence',
            ... "''", 'that', 'any', 'irregularities', 'took', 'place', '.'])
            ... # doctest: +ELLIPSIS
            1.682...

        :param n: the order of the language model (ngram size)
        :type n: int
        :param train: the training text
        :type train: list of string
        :param estimator: a function for generating a probability distribution
        :type estimator: a function that takes a ConditionalFreqDist and
              returns a ConditionalProbDist
        :param estimator_args: Extra arguments for estimator.
            These arguments are usually used to specify extra
            properties for the probability distributions of individual
            conditions, such as the number of bins they contain.
            Note: For backward-compatibility, if no arguments are specified, the
            number of bins in the underlying ConditionalFreqDist are passed to
            the estimator as an argument.
        :type estimator_args: (any)
        :param estimator_kw_args: Extra keyword arguments for estimator.
        :type estimator_kw_args: (any)
        """

        self._n = n

        if estimator is None:
            estimator = _estimator

        cfd = ConditionalFreqDist()
        self._ngrams = set()
        self._prefix = ('',) * (n - 1)

        for ngram in ingrams(chain(self._prefix, train), n):
            self._ngrams.add(ngram)
            context = tuple(ngram[:-1])
            token = ngram[-1]
            cfd[context].inc(token)

        if (not estimator_args) and (not estimator_kw_args):
            self._model = ConditionalProbDist(cfd, estimator, len(cfd))
        else:
            self._model = ConditionalProbDist(cfd, estimator, *estimator_args, **estimator_kw_args)

        # recursively construct the lower-order models
        if n > 1:
            self._backoff = NgramModel(n-1, train, estimator, *estimator_args, **estimator_kw_args)

    def prob(self, word, context):
        """
        Evaluate the probability of this word in this context using Katz Backoff.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: list(str)
        """

        context = tuple(context)
        if (context + (word,) in self._ngrams) or (self._n == 1):
            return self[context].prob(word)
        else:
            return self._alpha(context) * self._backoff.prob(word, context[1:])

    def _alpha(self, tokens):
        return self._beta(tokens) / self._backoff._beta(tokens[1:])

    def _beta(self, tokens):
        if tokens in self:
            return self[tokens].discount()
        else:
            return 1

    def logprob(self, word, context):
        """
        Evaluate the (negative) log probability of this word in this context.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: list(str)
        """

        return -log(self.prob(word, context), 2)

    def choose_random_word(self, context):
        '''
        Randomly select a word that is likely to appear in this context.

        :param context: the context the word is in
        :type context: list(str)
        '''

        return self.generate(1, context)[-1]

    # NB, this will always start with same word since model
    # is trained on a single text
    def generate(self, num_words, context=()):
        '''
        Generate random text based on the language model.

        :param num_words: number of words to generate
        :type num_words: int
        :param context: initial words in generated string
        :type context: list(str)
        '''

        text = list(context)
        for i in range(num_words):
            text.append(self._generate_one(text))
        return text

    def _generate_one(self, context):
        context = (self._prefix + tuple(context))[-self._n+1:]
        # print "Context (%d): <%s>" % (self._n, ','.join(context))
        if context in self:
            return self[context].generate()
        elif self._n > 1:
            return self._backoff._generate_one(context[1:])
        else:
            return '.'

    def entropy(self, text):
        """
        Calculate the approximate cross-entropy of the n-gram model for a
        given evaluation text.
        This is the average log probability of each word in the text.

        :param text: words to use for evaluation
        :type text: list(str)
        """

        e = 0.0
        # Add prefix to front to correctly handle first n-1 words
        text = list(self._prefix) + text
        for i in range(len(text)):
            context = tuple(text[i-self._n+1:i])
            token = text[i]
            e += self.logprob(token, context)
        return e / float(len(text) - (self._n-1))

    def perplexity(self, text):
        """
        Calculates the perplexity of the given text.
        This is simply 2 ** cross-entropy for the text.

        :param text: words to calculate perplexity of
        :type text: list(str)
        """

        return pow(2.0, self.entropy(text))

    def __contains__(self, item):
        return tuple(item) in self._model

    def __getitem__(self, item):
        return self._model[tuple(item)]

    def __repr__(self):
        return '<NgramModel with %d %d-grams>' % (len(self._ngrams), self._n)


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
