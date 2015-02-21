# -*- coding: utf-8 -*-
# Natural Language Toolkit: Language ID module using TextCat algorithm
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Avital Pekker <avital.pekker@utoronto.ca>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for language identification using the TextCat algorithm.
An implementation of the text categorization algorithm
presented in Cavnar, W. B. and J. M. Trenkle, 
"N-Gram-Based Text Categorization".

The algorithm takes advantage of Zipf's law and uses 
n-gram frequencies to profile languages and text-yet to
be identified-then compares using a distance measure.

Language n-grams are provided by the "An Crubadan"
project. A corpus reader was created seperately to read
those files.

For details regarding the algorithm, see:
http://www.let.rug.nl/~vannoord/TextCat/textcat.pdf

For details about An Crubadan, see:
http://borel.slu.edu/crubadan/index.html
"""

# Ensure that your own literal strings default to unicode rather than str.
from __future__ import print_function, unicode_literals

import nltk
from nltk.corpus import CrubadanCorpusReader
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist

from sys import maxint

# Note: this is NOT "re" you're likely used to. The regex module
# is an alternative to the standard re module that supports
# Unicode codepoint properties with the \p{} syntax.
# You may have to "pip install regx"
import regex as re  
######################################################################
##  Language identification using TextCat
######################################################################

class TextCat():

    _corpus = None
    fingerprints = {}
    _START_CHAR = "<".encode('utf8')
    _END_CHAR = ">".encode('utf8')
    
    last_distances = {}
    
    def __init__(self):
        self._corpus = CrubadanCorpusReader(nltk.data.find('corpora/crubadan'), '.*\.txt')
        
    def trigrams(self, text):
        padded_text = self._START_CHAR + text + self._END_CHAR
        trigrams = []
        # Generate 3-grams for given text
        for i in range(0, len(padded_text) - 2):
            cur_trigram = padded_text[i:(i + 3)]
            if len(cur_trigram) == 2:
                cur_trigram = cur_trigram + self._END_CHAR

            trigrams.append(cur_trigram)

        return trigrams

    def _print_trigrams(self, trigrams):
        for t in trigrams:
            print(t)
        
    def remove_punctuation(self, text):
        ''' Get rid of punctuation except apostrophes '''
        return re.sub(ur"[^\P{P}\']+", "", text.decode('utf8'))
    
    def profile(self, text):
        ''' Create FreqDist of trigrams within text '''
        clean_text = self.remove_punctuation(text)
        tokens = word_tokenize(clean_text)
        
        fingerprint = FreqDist()
        for t in tokens:
            token_trigrams = self.trigrams(t)
            for cur_trigram in token_trigrams:
                if cur_trigram in fingerprint:
                    fingerprint[cur_trigram] += 1
                else:
                    fingerprint[cur_trigram] = 1

        return fingerprint
        
    def calc_dist(self, lang, trigram, text_profile):
        ''' Calculate the "out-of-place" measure between the
            text and language profile for a single trigram '''
        lang_fd = self._corpus.all_lang_freq[lang]
        dist = 0
        
        if trigram in lang_fd:
            idx_lang_profile = lang_fd.keys().index(trigram)
            idx_text = text_profile.keys().index(trigram)

            dist = abs(idx_lang_profile - idx_text) 
        else:
            # Arbitrary but should be larger than
            # any possible trigram file length
            # in terms of total lines
            dist = maxint

        return dist
        
    def lang_dists(self, text):
        ''' Calculate the "out-of-place" measure between
            the text and all languages '''
        distances = {}
        profile = self.profile(text)
        # For all the languages
        for lang in self._corpus.all_lang_freq.keys():
            # Calculate distance metric for every trigram in
            # input text to be identified
            lang_dist = 0
            for trigram in profile:
                lang_dist += self.calc_dist(lang, trigram, profile)
        
            distances[lang] = lang_dist
            
        return distances
    
    def guess_language(self, text):
        ''' Find the language with the min distance
            to the text and return its ISO 639-3 code '''
        self.last_distances = self.lang_dists(text)
        
        return min(r, key=self.last_distances.get)
        
    def demo(self):
        ''' Demo of language guessing using a bunch of UTF-8 encoded
            text files with snippets of text copied from news websites
            around the web in different languages '''
        from os import listdir
        from os.path import isfile
        # Current dir
        path = '.'
        lang_samples = []
        
        for f in listdir(path):
            if isfile(f):
                m = re.match('sample_\w+\.txt', f)
                if m: lang_samples.append(f)
                
        print(lang_samples)
        for f in lang_samples:
            cur_sample = open(f, 'rU')
            cur_data = cur_sample.read()
            print('Language sample file: ' + f)
            print('Contents snippet:  ' + cur_data.decode('utf8')[0:140])
            print('#################################################')
            print('Language detection: ' + self.guess_language(cur_data))
            print('#################################################')

