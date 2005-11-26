# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

class ModelI:
    """
    A processing interface for assigning a probability to the next word.
    """

    def __init__(self):
        '''Create a new language model.'''
        raise NotImplementedError()

    def train(self, text):
        '''Train the model on the text.'''
        raise NotImplementedError()

    def probability(self, word, context):
        '''Evaluate the probability of this word in this context.'''
        raise NotImplementedError()

    def choose_random_word(self, context):
        '''Randomly select a word that is likely to appear in this context.'''
        raise NotImplementedError()

    def entropy(self, text):
        '''Evaluate the total entropy of a message with respect to the model.
        This is the sum of the log probability of each word in the message.'''
        raise NotImplementedError()

