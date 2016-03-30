# Natural Language Toolkit: API for Language Models
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT


class NgramModelI(object):
    """
    A processing interface for assigning a probability to the next word.
    """

    def __init__(self):
        '''Create a new language model.'''
        raise NotImplementedError()

    def score(self, word, context):
        '''Evaluate the probability of this word in this context.'''
        raise NotImplementedError()

    def logscore(self, word, context):
        '''Evaluate the (negative) log probability of this word in this context.'''
        raise NotImplementedError()

    def entropy(self, text):
        '''Evaluate the total entropy of a message with respect to the model.
        This is the sum of the log probability of each word in the message.'''
        raise NotImplementedError()
