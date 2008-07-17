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

    def __init__(self, n, train, probdist_factory, supply_condition=False, *factory_args):
        '''Create a new language model.'''

        self._n = n
        self._candidate_set_size = 10
        self._vocab = set()  # discard hapax legomena?

        fd = ConditionalFreqDist()
        for sentence in train:
            for index, token in enumerate(sentence):
                context = self.context(sentence, index)
                fd[context].inc(token)
		self._vocab.add(token)

        self._model = ConditionalProbDist(fd, probdist_factory,
                                          supply_condition, *factory_args)
        
    def context(self, tokens, index):
        return tuple(tokens[max(0,index-self._n+1):index])

    def prob(self, word, context):
        '''Evaluate the probability of this word in this context.'''
        return self._model[context].prob(word)

    def logprob(self, word, context):
        '''Evaluate the log probability of this word in this context.'''
        return self._model[context].logprob(word)

    def choose_random_word(self, context):
        '''Randomly select a word that is likely to appear in this context.'''
        # too simple: return self._model[context].max()

        probs = [(self.prob(word, context), word) for word in self._vocab]
        probs.sort()  # wasteful for finding n-best
        return random.choice(probs[:self._candidate_set_size])

    def generate(self, n):
        tokens = []
        for i in range(n):
            c = self.context(tokens, i)
            tokens.append(self.choose_random_word(c))
        return tokens

    def entropy(self, sentence):
        '''Evaluate the total entropy of a message with respect to the model.
        This is the sum of the log probability of each word in the message.'''

        e = 0.0
        for index, token in enumerate(sentence):
            context = self.context(sentence, index)
            e -= self.logprob(token, context)
        return e

    def __repr__(self):
        return '<NgramModel with vocabulary of %d words>' % len(self._vocab)

def demo():
    from nltk.corpus import brown
    lm = NgramModel(2, brown.sents(categories='a'), MLEProbDist)
    print lm
    sent = brown.sents()[0]
    print sent
    print lm.entropy(sent)
    print lm.generate(20)

if __name__ == '__main__':
    demo()

