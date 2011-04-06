# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import random
from itertools import chain
from math import log

from nltk.probability import (ConditionalProbDist, ConditionalFreqDist,
                              MLEProbDist, SimpleGoodTuringProbDist)
from nltk.util import ingrams

from api import *

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
    def __init__(self, n, train, estimator=None):
        """
        Creates an ngram language model to capture patterns in n consecutive
        words of training text.  An estimator smooths the probabilities derived
        from the text and may allow generation of ngrams not seen during
        training.

        @param n: the order of the language model (ngram size)
        @type n: C{int}
        @param train: the training text
        @type train: C{list} of C{string}
        @param estimator: a function for generating a probability distribution
        @type estimator: a function that takes a C{ConditionalFreqDist} and
              returns a C{ConditionalProbDist}
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

        self._model = ConditionalProbDist(cfd, estimator, len(cfd))

        # recursively construct the lower-order models
        if n > 1:
            self._backoff = NgramModel(n-1, train, estimator)

    # Katz Backoff probability
    def prob(self, word, context):
        """
        Evaluate the probability of this word in this context.
        """

        context = tuple(context)
        if context + (word,) in self._ngrams:
            return self[context].prob(word)
        elif self._n > 1:
            return self._alpha(context) * self._backoff.prob(word, context[1:])
        else:
            raise RuntimeError("No probability mass assigned to word %s in " +
                               "context %s" % (word, ' '.join(context)))

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
        """

        return -log(self.prob(word, context), 2)

    def choose_random_word(self, context):
        '''Randomly select a word that is likely to appear in this context.'''
        return self.generate(1, context)[-1]

    # NB, this will always start with same word since model
    # is trained on a single text
    def generate(self, num_words, context=()):
        '''Generate random text based on the language model.'''
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
        Evaluate the total entropy of a text with respect to the model.
        This is the sum of the log probability of each word in the message.
        """

        e = 0.0
        for i in range(self._n - 1, len(text)):
            context = tuple(text[i-self._n+1:i])
            token = text[i]
            e += self.logprob(token, context)
        return e

    def __contains__(self, item):
        return tuple(item) in self._model

    def __getitem__(self, item):
        return self._model[tuple(item)]

    def __repr__(self):
        return '<NgramModel with %d %d-grams>' % (len(self._ngrams), self._n)

def demo():
    from nltk.corpus import brown
    from nltk.probability import LidstoneProbDist, WittenBellProbDist
    estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
#    estimator = lambda fdist, bins: WittenBellProbDist(fdist, 0.2)
    lm = NgramModel(3, brown.words(categories='news'), estimator)
    print lm
#    print lm.entropy(sent)
    text = lm.generate(100)
    import textwrap
    print '\n'.join(textwrap.wrap(' '.join(text)))

if __name__ == '__main__':
    demo()
