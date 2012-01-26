# Natural Language Toolkit: API for Language Models
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


# should this be a subclass of ConditionalProbDistI?

class ModelI(object):
    """
    A processing interface for assigning a probability to the next word.
    """

    def __init__(self):
        '''Create a new language model.'''
        raise NotImplementedError()

    def prob(self, word, context):
        '''Evaluate the probability of this word in this context.'''
        raise NotImplementedError()

    def logprob(self, word, context):
        '''Evaluate the (negative) log probability of this word in this context.'''
        raise NotImplementedError()

    def choose_random_word(self, context):
        '''Randomly select a word that is likely to appear in this context.'''
        raise NotImplementedError()

    def generate(self, n):
        '''Generate n words of text from the language model.'''
        raise NotImplementedError()

    def entropy(self, text):
        '''Evaluate the total entropy of a message with respect to the model.
        This is the sum of the log probability of each word in the message.'''
        raise NotImplementedError()

