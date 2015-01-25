# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford NER-tagger
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Long Duong <longdt219@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for interfacing with the Mallet CRF taggers.
"""

import os
import tempfile
from subprocess import PIPE
import unicodedata
import re 

from nltk.internals import find_jar, config_java, java, _java_options
from nltk.tag.api import TaggerI

_mallet_url = 'http://mallet.cs.umass.edu/grmm/'

class MalletTagger(TaggerI):
    """
    An interface to Mallet CRF taggers.
    
    >>> from nltk.tag.mallet import MalletTagger
    >>> mt = MalletTagger('/Users/HeroAthen/Dropbox/Work/nltk/temp/mallet-2.0.7/dist/mallet.jar', 
    ... '/Users/HeroAthen/Dropbox/Work/nltk/temp/mallet-2.0.7/dist/mallet-deps.jar')
 
    >>> train_data = [[('University','Noun'), ('is','Verb'), ('a','Det'), ('good','Adj'), ('place','Noun')],
    ... [('dog','Noun'),('eat','Verb'),('meat','Noun')]]
    
    >>> mt.train(train_data,'model.crf.tagger')
    >>> mt.tag_sents([['dog','is','good'], ['Cat','eat','meat']])
    [[('dog', 'Noun'), ('is', 'Verb'), ('good', 'Noun')], [('Cat', 'Noun'), ('eat', 'Verb'), ('meat', 'Noun')]]
    
    >>> gold_sentences = [[('dog','Noun'),('is','Verb'),('good','Adj')] , [('Cat','Noun'),('eat','Verb'), ('meat','Noun')]] 
    >>> mt.evaluate(gold_sentences) - 0.83333 < 0.0001
    True
    
    Test the function of finding jar file in the environment variable and setting learned model file  
    >>> mt = MalletTagger() 
    >>> mt.set_model_file('model.crf.tagger')
    >>> mt.evaluate(gold_sentences) - 0.83333 < 0.0001
    True 
    
    """
    
    _JAR = 'mallet.jar'
    _JAR_DEPS = 'mallet-deps.jar'

    def __init__(self, path_to_mallet_jar=None, path_to_mallet_deps_jar = None, verbose=False, java_options='-mx1000m'):

        self._mallet_jar = find_jar(
                self._JAR, path_to_mallet_jar,
                env_vars=('MALLET',), searchpath=(), url=_mallet_url,
                verbose=verbose)
        
        self._mallet_dep_jar = find_jar(
                self._JAR_DEPS, path_to_mallet_deps_jar,
                env_vars=('MALLET_DEPS',), searchpath=(), url=_mallet_url,
                verbose=verbose) 
        
        self.java_options = java_options
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
        
        >>> from nltk.tag.mallet import MalletTagger
        >>> mt = MalletTagger()
        >>> mt._get_features(u'University1')
        u'WORD_University1 CAPITALIZATION HAS_NUM SUF_1 SUF_y1 SUF_ty1'
        >>> mt._get_features(u'.?')
        u'WORD_.? PUNCTUATION SUF_?'
        """ 
        feature_list = 'WORD_' + data + ' ' 
        # Capitalization 
        if data[0].isupper():
            feature_list += 'CAPITALIZATION '
        
        # Number 
        pattern = re.compile('\\d')
        if re.search(pattern, data) is not None:
            feature_list += 'HAS_NUM ' 
        
        # Punctuation
        punc_cat = set(["Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"])
        if all (unicodedata.category(x) in punc_cat for x in data):
            feature_list += 'PUNCTUATION '
        
        # Suffix up to length 3
        if len(data) > 1:
            feature_list += ('SUF_' + data[-1:] + ' ') 
        if len(data) > 2: 
            feature_list += ('SUF_' + data[-2:] + ' ')    
        if len(data) > 3: 
            feature_list += ('SUF_' + data[-3:] + ' ')
        
        return feature_list.strip()
        
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
        
        # We need the list of sentences instead of the list generator for matching the input and output  
        sentences = list(sents) 
        
        # First, build the test file 
        input_file = tempfile.NamedTemporaryFile(
                prefix='mallet_tagger.test',
                dir=tempfile.gettempdir(),
                delete=False)

        for sent in sentences: 
            for token in sent:
                data = unicode(token)
                input_file.write(self._get_features(data) + '\n')
            input_file.write('\n')
        
        input_file.close()
        
        # Now use the model to tag
        
        default_options = ' '.join(_java_options)
        config_java(options=self.java_options, verbose=False)
        
        self._cmd = ['cc.mallet.fst.SimpleTagger', '--model-file', self._model_file, input_file.name ]
        
        class_path = self._mallet_dep_jar + ':' + self._mallet_jar 
        stand_output, _stderr = java(self._cmd,classpath=class_path, stdout=PIPE, stderr=PIPE)
        
        # Return java configurations to their default values
        config_java(options=default_options, verbose=False)
        
        # Remove the temp file 
        os.remove(input_file.name)
        
        return self.parse_output(stand_output, sentences)
        
    
    def train(self, train_data, model_file):
        '''
        Train the CRF tagger using Mallet  
        :params train : is the list of annotated sentences.        
        :type train : list (list(tuple(str,str)))
        :params model_file : the model will be saved to this file.     
         
        '''
        
        try:
            input_file = tempfile.NamedTemporaryFile(
                prefix='mallet_tagger.train',
                dir=tempfile.gettempdir(),
                delete=False)

            for sent in train_data:
                for data,label in sent:
                    data = unicode(data)
                    input_file.write(self._get_features(data) + ' ' + label + '\n')
                input_file.write('\n')            
            input_file.close()
            
            # Now train the model
            default_options = ' '.join(_java_options)
            config_java(options=self.java_options, verbose=False)
            
            self._cmd = ['cc.mallet.fst.SimpleTagger',
                '--train', 'true', '--model-file', model_file, input_file.name ]
            
            # Run the java command
            class_path = self._mallet_dep_jar + ':' + self._mallet_jar 
            stand_output, _stderr = java(self._cmd,classpath=class_path, stdout=PIPE, stderr=PIPE)
            # Return java configurations to their default values
            config_java(options=default_options, verbose=False)
            
            # Save the model file 
            self._model_file = model_file            
        finally:
            os.remove(input_file.name)

    def tag(self, tokens):
        '''
        Tag a sentence using Mallet CRF Tagger. NB before using this function, user should specify the mode_file either by 
                       - Train a new model using ``train'' function 
                       - Use the pre-trained model which is set via ``set_model_file'' function  
        :params tokens : list of tokens needed to tag. 
        :type tokens : list(str)
        :return : list of tagged tokens. 
        :rtype : list (tuple(str,str)) 
        '''
        
        return self.tag_sents([tokens])[0]

    def parse_output(self, text, sentences):
        
        labels= []
        sent_labels = []
        for label in text.strip().split("\n"):
            label = label.strip()
            if label == '':
                sent_labels.append(labels)
                labels = []
                continue 
            labels.append(label)
            
        if len(labels) > 0:
            sent_labels.append(labels)
            
        # Match labels with word 
        if len(sentences) != len(sent_labels):
            raise ValueError(' Expecting error, number of sentence is not matched')
        tagged_sentences = []
         
        for i  in range(len(sentences)):
            words = sentences[i]  
            labels = sent_labels[i]
         
            if len(words) != len(labels):
                raise ValueError(' Expecting error, sentence length is not matched')
            tagged_sentence = []
            for j in range(len(words)):
                tagged_sentence.append((words[j],labels[j]))
            tagged_sentences.append(tagged_sentence)
            
        return tagged_sentences

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
