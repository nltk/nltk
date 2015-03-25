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
try:
    import regex as re
except ImportError:
    re = None
######################################################################
##  Language identification using TextCat
######################################################################

class TextCat(object):

    _corpus = None
    fingerprints = {}
    _START_CHAR = "<".encode('utf8')
    _END_CHAR = ">".encode('utf8')
    
    last_distances = {}
    
    def __init__(self):
        if not re:
            raise EnvironmentError("classify.textcat requires the regex module that "
                                   "supports unicode. Try '$ pip install regex' and "
                                   "see https://pypi.python.org/pypi/regex for "
                                   "further details.")

        self._corpus = CrubadanCorpusReader(nltk.data.find('corpora/crubadan'), '.*\.txt')
        # Load all language ngrams into cache
        for lang in self._corpus.langs():
            self._corpus.lang_freq(lang)
        
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
        
        lang_fd = self._corpus.lang_freq(lang)
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
        for lang in self._corpus._all_lang_freq.keys():
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
        
        return min(self.last_distances, key=self.last_distances.get)
        #################################################')

    def demo(self):
        from nltk.corpus import udhr

        langs = ['Kurdish-UTF8', 'Abkhaz-UTF8', 'Farsi_Persian-UTF8',
                 'Hindi-UTF8', 'Hawaiian-UTF8', 'Russian-UTF8', 'Vietnamese-UTF8',
                 'Serbian_Srpski-UTF8','Esperanto-UTF8']

        friendly = {'kmr':'Northern Kurdish',
                    'abk':'Abkhazian',
                    'pes':'Iranian Persian',
                    'hin':'Hindi',
                    'haw':'Hawaiian',
                    'rus':'Russian',
                    'vie':'Vietnamese',
                    'srp':'Serbian',
                    'epo':'Esperanto'}
        
        for cur_lang in langs:
            # Get raw data from UDHR corpus
            raw_sentences = udhr.sents(cur_lang)
            rows = len(raw_sentences) - 1
            cols = map(len, raw_sentences)

            sample = ''
          
            # Generate a sample text of the language
            for i in range(0, rows):
                cur_sent = ''
                for j in range(0, cols[i]):
                    cur_sent += ' ' + raw_sentences[i][j]
            
                sample += cur_sent
          
            # Try to detect what it is
            print('Language snippet: ' + sample[0:140] + '...')
            guess = self.guess_language(sample.encode('utf8'))
            print('Language detection: %s (%s)' % (guess, friendly[guess]))
            print('#' * 140)