# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the CRFSuite Tagger
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Long Duong <longdt219@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for interfacing with the CRFSuite taggers.
"""
from __future__ import absolute_import
from __future__ import unicode_literals
import unicodedata
import re 
from nltk.tag.api import TaggerI
import pycrfsuite

_py_crfsuite_url = 'https://pypi.python.org/pypi/python-crfsuite'


class CRFTagger(TaggerI):
    """
    An interface to Python CRFSuite taggers. https://pypi.python.org/pypi/python-crfsuite
    
    >>> from nltk.tag.crfsuite import CRFTagger
    >>> ct = CRFTagger()
 
    >>> train_data = [[('University','Noun'), ('is','Verb'), ('a','Det'), ('good','Adj'), ('place','Noun')],
    ... [('dog','Noun'),('eat','Verb'),('meat','Noun')]]
    
    >>> ct.train(train_data,'model.crf.tagger')
    >>> ct.tag_sents([['dog','is','good'], ['Cat','eat','meat']])
    [[('dog', 'Noun'), ('is', 'Verb'), ('good', 'Adj')], [('Cat', 'Noun'), ('eat', 'Verb'), ('meat', 'Noun')]]
    
    >>> gold_sentences = [[('dog','Noun'),('is','Verb'),('good','Adj')] , [('Cat','Noun'),('eat','Verb'), ('meat','Noun')]] 
    >>> ct.evaluate(gold_sentences) 
    1.0
    
    Setting learned model file  
    >>> ct = CRFTagger() 
    >>> ct.set_model_file('model.crf.tagger')
    >>> ct.evaluate(gold_sentences)
    1.0
    
    """
    
    def __init__(self, file_path=''):
               
        self._model_file = ''
    

    def set_model_file(self, model_file):
        self._model_file = model_file
            
    def _get_features(self,data):
        """
        Extract basic features about this word including 
             - Current Word 
             - Is Capitalized ?
             - Has Punctuation ?
             - Has Number ?
             - Suffixes up to length 3 
        :return : a string which contains the features   
        
        """ 
        feature_list = []  
        # Capitalization 
        if data[0].isupper():
            feature_list.append('CAPITALIZATION')
        
        # Number 
        pattern = re.compile('\\d')
        if re.search(pattern, data) is not None:
            feature_list.append('HAS_NUM') 
        
        # Punctuation
        punc_cat = set(["Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"])
        if all (unicodedata.category(x) in punc_cat for x in data):
            feature_list.append('PUNCTUATION')
        
        # Suffix up to length 3
        if len(data) > 1:
            feature_list.append('SUF_' + data[-1:]) 
        if len(data) > 2: 
            feature_list.append('SUF_' + data[-2:])    
        if len(data) > 3: 
            feature_list.append('SUF_' + data[-3:])
            
        feature_list.append('WORD_' + data )
        
        return feature_list
        
    def tag_sents(self, sents):
        '''
        Tag a list of sentences. NB before using this function, user should specify the mode_file either by 
                       - Train a new model using ``train'' function 
                       - Use the pre-trained model which is set via ``set_model_file'' function  
        :params sentences : list of sentences needed to tag. 
        :type sentences : list(list(str))
        :return : list of tagged sentences. 
        :rtype : list (list (tuple(str,str))) 
        '''
        tagger = pycrfsuite.Tagger()
        tagger.open(self._model_file)
        # We need the list of sentences instead of the list generator for matching the input and output
        result = []  
        for sent in sents:
            features = [self._get_features(data) for data in sent]
            labels = tagger.tag(features)
                
            if len(labels) != len(sent):
                raise Exception(' Predicted Length Not Matched, Expect Errors !')
            
            tagged_sent = [(sent[i],labels[i]) for i in range(len(labels))]

            result.append(tagged_sent)
            
        return result 
    
    def train(self, train_data, model_file):
        '''
        Train the CRF tagger using CRFSuite  
        :params train_data : is the list of annotated sentences.        
        :type train_data : list (list(tuple(str,str)))
        :params model_file : the model will be saved to this file.     
         
        '''
        X_train = []
        y_train = [] 
        
        for sent in train_data:
            features = [self._get_features(data) for data,label in sent]
            labels = [label for data,label in sent]
            
            X_train.append(features)
            y_train.append(labels)    
            
        # Now train the model, the output should be model_file
        trainer = pycrfsuite.Trainer(verbose=False)
        for xseq, yseq in zip(X_train, y_train):
            trainer.append(xseq, yseq)
        trainer.train(model_file)
        # Save the model file 
        self._model_file = model_file            

    def tag(self, tokens):
        '''
        Tag a sentence using Python CRFSuite Tagger. NB before using this function, user should specify the mode_file either by 
                       - Train a new model using ``train'' function 
                       - Use the pre-trained model which is set via ``set_model_file'' function  
        :params tokens : list of tokens needed to tag. 
        :type tokens : list(str)
        :return : list of tagged tokens. 
        :rtype : list (tuple(str,str)) 
        '''
        
        return self.tag_sents([tokens])[0]

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
