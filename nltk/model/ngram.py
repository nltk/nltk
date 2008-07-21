# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import random

from nltk.probability import ConditionalProbDist, ConditionalFreqDist, MLEProbDist

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
        for sentence in train:
            for index, token in enumerate(sentence):
                context = self.context(sentence, index)
                cfd[context].inc(token)

        self._model = ConditionalProbDist(cfd, estimator, False, len(cfd))

        # recursively construct the lower-order models
        if n>1:
            self._backoff_model = NgramModel(n-1, train, estimator)

    def context(self, tokens, index):
        return tuple(tokens[max(0,index-self._n+1):index])

    # Katz Backoff probability
    def prob(self, word, context):
        '''Evaluate the probability of this word in this context.'''

        # C(w_<i-n+1,i>) > 0
        if context in self and word in self[context].freqdist():
            return self[context].prob(word)

        # C(w_<i-n+2,i>) > 0
        if context[:-1] in self._backoff_model and word in self._backoff_model[context[:-1]].freqdist():
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
        text = list(context)
        for i in range(n):
            print self.context(text, i), self._model[self.context(text, i)]
            word = self._model[self.context(text, i)].generate()
            text.append(word)
        return text

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
        for index, token in enumerate(text):
            context = self.context(text, index)
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
    lm = NgramModel(3, brown.sents(categories='a'), estimator)
    print lm
    sent = brown.sents()[0]
    print sent
#    print lm.entropy(sent)
    print lm.generate(40)

if __name__ == '__main__':
    demo()

