# -*- coding: utf-8 -*-
# Natural Language Toolkit: Machine Translation
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Liling Tan
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
#

from util import read_phrase_table, read_lang_model

class LanguageModel:
    """
    This class implements an Ngram language model object that reads an ARPA 
    language model file and allow users to retrieve the probability of a 
    word given the current `state` of a word (i.e. the previous words prior to 
    the word). 
    
    For instance, we want to know how often the word 'rudimentary' occurs
    after the phrase 'the most'. We say that the current language state is
    ('the', 'most') and we want to retrieve the logarithmic probability of the
    word 'rudimentary', given the state:
    
    >>> lm = LanguageModel('europarl.srilm.gz')
    >>> state = 'the most'
    >>> word = 'rudimentary'
    >>> new_state, score = lm.score(state, word)
    >>> score
    -3.242284
    
    Another example, for the word 'opponent' coming after the word 'tough':
    
    >>> lm = LanguageModel('europarl.srilm.gz')
    >>> state = 'tough'
    >>> word = 'opponent'
    >>> new_state, score = lm.score(state, word)
    >>> score
    -2.658133
    """    
    def __init__(self, arpafile):
        self.table = read_lang_model(arpafile)
        
    def score(self, state, word, n=2):
        """
        This modules returns a score of a word given the state of word.
        If the full ngram (i.e. state+word) is in the language model, simply
        retrieves the log probabilities from the table.
        
        Otherwise, calculates the sum of log prob from the possible ngrams,
        e.g. if `state = '
        
        :type state: str
        :param state: the preceedings words before the word in concern. 
        
        :rtype: tuple
        :return: a tuple of the new state and its probabilistic score
        """
        # Converts a string into tuples as stored how language model was read.
        if isinstance(state, str):
            state = tuple(state.split())
        word = tuple(word.split())
        ngram = state + word
        score = 0.0
        while ngram: 
            # If the full ngram is the language model.
            if ngram in self.table:
                # Retrieves the ngram log probability from the language model.
                return (ngram[-n:], score + self.table[ngram][0])
            # Calculates the sum of log probabilities of possible ngrams.
            # aka. the backoff probability. 
            else:
                # Retrieves the log prob of the ngram without the final word.
                score += self.table[ngram[:-1]][1] if len(ngram) > 1 else 0.0
                # Reduces the ngram by  
                ngram = ngram[1:]
        return ((), score + self.table[("<unk>",)][0])

class TranslationModel:
    """
    This class implements an translation model object.
    To retrieve the possible translation of a phrase, use:
    
    >>> tm = TranslationModel('phrase-table')
    >>> tm.table['es gibt']
    {'there is': 1.0}
    
    Note:
    For now, the translation model object only retrieves the probabilities from
    the `phrasetablefile`. However this object can be modified in future 
    development when implementing other variants of the translation model, e.g.
    scaling the data by adding phrase tables from an external source, adding
    dictionary, etc.
    """
    def __init__(self, phrasetablefile):
        self.table = read_phrase_table(phrasetablefile)

# run doctests
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    