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
import os
import tempfile
from subprocess import PIPE
import unicodedata
import re 
from subprocess import Popen
from nltk.tag.api import TaggerI

_crfsuite_url = 'http://www.chokkan.org/software/crfsuite'

class CRFTagger(TaggerI):
    """
    An interface to CRFSuite taggers. http://www.chokkan.org/software/crfsuite/tutorial.html
    
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
    
    def __init__(self, cmd_options=''):
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
        feature_list = ''  
        # Capitalization 
        if data[0].isupper():
            feature_list += 'CAPITALIZATION\t'
        
        # Number 
        pattern = re.compile('\\d')
        if re.search(pattern, data) is not None:
            feature_list += 'HAS_NUM\t' 
        
        # Punctuation
        punc_cat = set(["Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"])
        if all (unicodedata.category(x) in punc_cat for x in data):
            feature_list += 'PUNCTUATION\t'
        
        # Suffix up to length 3
        if len(data) > 1:
            feature_list += ('SUF_' + data[-1:] + '\t') 
        if len(data) > 2: 
            feature_list += ('SUF_' + data[-2:] + '\t')    
        if len(data) > 3: 
            feature_list += ('SUF_' + data[-3:] + '\t')
        feature_list +=  'WORD_' + data + '\t'
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
                prefix='crf_tagger.test',
                dir=tempfile.gettempdir(),
                delete=False)

        for sent in sentences: 
            for token in sent:
                #data = unicode(token)
                data = token
                input_file.write(('DUMMY_LABEL\t' + self._get_features(data) + '\n').encode('utf-8'))
            input_file.write('\n'.encode('utf-8'))
        
        input_file.close()
        
        # Now use the model to tag
        _crf_cmd = ['crfsuite', 'tag', '-m', self._model_file, input_file.name]
            
            
        # Run the tagger and get the output
        p = Popen(_crf_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p.communicate()

        # Check the return code.
        if p.returncode != 0:
            raise Exception('CRFSuite command failed! Details: %s' % stderr)
        
        # Remove the temp file
        #print ('Test file : ' + input_file.name) 
        os.remove(input_file.name)
        
        return self.parse_output(stdout, sentences)
        
    
    def train(self, train_data, model_file):
        '''
        Train the CRF tagger using CRFSuite  
        :params train : is the list of annotated sentences.        
        :type train : list (list(tuple(str,str)))
        :params model_file : the model will be saved to this file.     
         
        '''
        
        try:
            input_file = tempfile.NamedTemporaryFile(
                prefix='crf_tagger.train',
                dir=tempfile.gettempdir(),
                delete=False)

            for sent in train_data:
                for data,label in sent:
                    #data = unicode(data)
                    input_file.write((label + '\t' + self._get_features(data) + '\n').encode('utf-8'))
                input_file.write('\n'.encode('utf-8'))            
            input_file.close()
            
            # Now train the model, the output should be model_file
            _crf_cmd = ['crfsuite', 'learn', '-m', model_file, input_file.name]
            
            # Serialize the actual sentences to a temporary string
            # Run the tagger and get the output
            p = Popen(_crf_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            (stdout, stderr) = p.communicate()

            # Check the return code.
            if p.returncode != 0:
                raise Exception('CRFSuite command failed! Details: %s' % stderr)
            
            # Save the model file 
            self._model_file = model_file            
        finally:
            os.remove(input_file.name)
            #print ('Training data : ' + input_file.name)

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
        text = text.decode('utf-8')
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
            raise ValueError(' Expecting error, number of sentence is not matched' + str(len(sentences)) + ' vs ' + str(len(sent_labels)))
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
