# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import random

from nltk.probability import ConditionalProbDist, ConditionalFreqDist, MLEProbDist
from nltk.utilities import ingram

from api import *

class NgramModel(ModelI):
    """
    A processing interface for assigning a probability to the next word.
    """

    # add cutoff
    def __init__(self, n, train, estimator=None):
        """
        Creates an ngram language model to capture patterns in n consecutive
        words of training text.  An estimator smooths the probabilities derived
        from the text and may allow generation of ngrams not seen during training.

        @param n: the order of the language model (ngram size)
        @type n: C{int}
        @param train: the training text
        @type train: C{list} of C{list} of C{string}
        @param estimator: a function for generating a probability distribution
        @type estimator: a function that takes a C{ConditionalFreqDist} and returns
              a C{ConditionalProbDist}
        """

        self._n = n
        
        if estimator == None:
            estimator = lambda fdist, bins: MLEProbDist(fdist)

        cfd = ConditionalFreqDist()
        for ngram in ingram(train, n):
            cfd[ngram[:-1]].inc(ngram[-1])

        self._model = ConditionalProbDist(cfd, estimator, False, len(cfd))

        # recursively construct the lower-order models
        if n>1:
            self._backoff_model = NgramModel(n-1, train, estimator)

    # Katz Backoff probability
    def prob(self, word, context):
        '''Evaluate the probability of this word in this context.'''

        print "HERE"
        
        # C(w_<i-n+1,i>) > 0
        if self._attested(word, context):
            print context, word, self[context].prob(word)
            return self[context].prob(word)

        # C(w_<i-n+2,i>) > 0
        if self._backoff_model._attested(word, context[:-1]):
            print context[:-1], word, self._alpha(context) * self._backoff_model.prob(word, context[:-1])
            return self._alpha(context) * self._backoff_model.prob(word, context[:-1])

        print "Unreachable?"
        # C(w_<i-n+2,i>) = 0   (redundant, since alpha=1 in this case?)
        return self._backoff_model.prob(word, context[:-1])

# add Katz backoff
#    def logprob(self, word, context):
#        '''Evaluate the log probability of this word in this context.'''
#        return self._model[context].logprob(word)

    # todo: implement Katz backoff
    def generate(self, n, context=()):
        context = list(context)
        for i in range(n):
            next = self._generate_one(context)
            text.append(next)
            context.append(next)
            if len(context) >= self._n:
                context = context[-self._n+1:]
        return text

    def _generate_one(self, context):
        if context in self and random.random() > self[context].discount():
            return self[context].generate()
        elif self._n > 1:
            return self._backoff_model._generate_one(context[:-1])
        else:
            return '.'
    
    def _attested(self, word, context):
        return context in self and word in self[context].freqdist()

    def _alpha(self, tokens):
        return self._beta(tokens) / self._backoff_model._beta(tokens[:-1])

    def _beta(self, tokens):
        if tokens in self:
            return self[tokens].discount()
        else:
            return 1

    def entropy(self, text):
        '''Evaluate the total entropy of a text with respect to the model.
        This is the sum of the log probability of each word in the message.'''

        e = 0.0
        for i in range(self._n - 1, len(text)):
            context = tuple(text[i - self._n + 1, i - 1])
            token = text[i]
            e -= self.logprob(token, context)
        return e

    def __in__(self, item):
        return tuple(item) in self._model

    def __getitem__(self, item):
        return self._model[tuple(item)]

    def __repr__(self):
        return '<NgramModel with %d %d-grams>' % (len(self._model), self._n)

def demo():
    from nltk.corpus import brown
    from nltk.probability import LidstoneProbDist
    estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
    lm = NgramModel(3, brown.words(categories='a'), estimator)
    print lm
    sent = brown.sents()[0]
    print sent
#    print lm.entropy(sent)
    print lm.generate(40)

if __name__ == '__main__':
    demo()

