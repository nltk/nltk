# -*- coding: utf-8 -*-
# Natural Language Toolkit: Phrase Extraction Algorithm
#
# Copyright (C) 2001-2014 NLTK Project
# Authors: Liling Tan
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import gzip, mimetypes

def read_phrase_table(phrasetablefile):
    """
    This module reads a phrase table file that is commonly used by 
    machine translation decoder. The phrase table file is a tab-separated file.
    Each line of the phrase table file contains the:
    a.   source phrase
    b.  target phrase 
    c. translation probabilities 
        c1. inverse phrase translation probability φ(f|e)
        c2. inverse lexical weighting lex(f|e)
        c3. direct phrase translation probability φ(e|f)
        c4. direct lexical weighting lex(e|f)
    d.  word alignments (in pharaoh format)
    
    When translating from source language, e, to target language, f, the noisy
    channel model requires the φ(f|e).
    
    For more information of the phrase table file format, 
    see http://www.statmt.org/moses/?n=FactoredTraining.ScorePhrases 
    
    :type phrasetablefile: str
    :param phrasetablefile: the filename for the phrase table .gz file. 
    
    :rtype: dict
    :return: a dictionary of dictionary where the keys are the source language 
    phrases and their values are a dictionary of the target language phrases 
    and its probability.
    
    >>> x = read_phrase_table('phrase-table')
    >>> print x
    {'es gibt': {'there is': 1.0}, 'klein': {'small': 0.8, 'little': 0.8}, 'die': {'the': 0.3}, 'der': {'the': 0.3}, 'haus': {'house': 1.0}, 'ist': {'is': 1.0, "'s": 1.0}, 'kleines': {'small': 0.2, 'little': 0.2}, 'gibt': {'gives': 1.0}, 'es ist': {'this is': 0.2, 'it is': 0.8}, 'das': {'this': 0.1, 'the': 0.4, 'it': 0.1}, 'alt': {'old': 0.8}, 'ein': {'a': 1.0, 'an': 1.0}, 'altes': {'old': 0.2}, 'das ist': {'this is': 0.8, 'it is': 0.2}}
    >>> print x['es gibt']
    {'there is': 1.0}
    """
    phrase_table = {}
    
    # Checks if phrase table file is gzip file format.
    if mimetypes.guess_type(phrasetablefile)[1] == 'gzip':
        anyopen = gzip.open
    else: 
        anyopen = open
    
    with anyopen(phrasetablefile, 'rb') as fin:
        for line in fin:
            # Splits the tab separated file.
            line = line.strip().split(' ||| ')
            # Only first three columns are necessary for phrase-based MT.
            src, trg, probabilities = line[:3]
            # Only the φ(f|e) is required.
            prob = float(probabilities.split( )[0])
            phrase_table.setdefault(src, {})[trg]= prob
        
    return phrase_table

def read_lang_model(arpafile):
    """
    The module reads a ngram language model file in ARPA format. 
    The ngram probabilities and backoff probabilities are stored in 
    tab-separated columns, each row represents an ngram and its probabilities.
    For example:
    
        \data\
        ngram 1=37344
        ngram 2=715602
        
        \1-grams:
        -2.785123    </s>
        -99    <s>    -1.750062      
        
        \2-grams:
        -1.226477    it is    -1.013582
        
    The first column stores the log probabitlity of the ngram
    The second column stores the surface string of the ngram
    The third column stores the backoff probabitlites of the ngram
    
    Note: Rows with less than 2 columns can be ignored as they do not store the
    ngrams, they are usually meta-data on the ngram extracted or comment lines
    to separated to n from the n+1 grams.
    
    For more information on the ARPA format, see
    http://www.speech.sri.com/projects/srilm/manpages/ngram-format.5.html
    
    :type arpafile: str
    :param arpafile: the filename for the phrase table .gz file. 
    
    :rtype: dict
    :return: a dictionary of dictionary where the key is the source language 
    phrase and its value is a dictionary of the target language phrase and its
    probability.

    >>> y = read_lang_model('europarl.srilm.gz')
    >>> print y[('<s>',)]
    (-99.0, -1.750062)
    """
    lang_model = {}
    with gzip.open(arpafile, 'rb') as fin:
        for line in fin:
            line = line.strip().split('\t')
            if len(line) > 1:
                try: # When backoff is available.
                    prob, ngram, backoff = line[:3]
                except ValueError: # When backoff is not available.
                    prob, ngram, backoff = line[:2] + [0]
                lang_model[tuple(ngram.split())] = (float(prob), float(backoff))
    # Sets a default for unknown words if <unk> not in language model.
    if '<unk>' not in lang_model.keys():
        lang_model[('<unk>',)] = (float(-100), 0)
    return lang_model

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

