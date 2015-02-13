# -*- coding: utf-8 -*-
# Natural Language Toolkit: An Crubadan N-grams Reader
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Avital Pekker <avital.pekker@utoronto.ca>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
An NLTK interface for the n-gram statistics gathered from
the corpora for each language using An Crubadan.

There are multiple potential applications for the data but
this reader was created with the goal of using it in the
context of language identification.

For details about An Crubadan, this data, and its potential uses, see:
http://borel.slu.edu/crubadan/index.html
"""

# Ensure that your own literal strings default to unicode rather than str.
from __future__ import print_function, unicode_literals

from nltk.corpus.reader import CorpusReader
from nltk.probability import FreqDist
from nltk.data import ZipFilePathPointer

import re
from re import escape, search
######################################################################
##  An Crubadan N-gram Corpus Reader
######################################################################

class CrubadanCorpusReader(CorpusReader):
    """
    A corpus reader used to access language An Crubadan n-gram files.
    """
    
    _LANG_MAPPER_FILE = 'table.txt'
    all_lang_freq = {}
    
    def __init__(self, root, fileids, encoding='utf8', tagset=None):
        super(CrubadanCorpusReader, self).__init__(root, fileids, encoding='utf8')
        self._lang_mapping_data = []
        self._load_lang_mapping_data()
    
    def load_all_ngrams(self):
        ''' Create a dictionary of every supported language mapping 
            the ISO 639-3 language code to its corresponding n-gram
            FreqDist. The result can be accessed via "all_lang_freq" var '''
        
        # Filter out non n-gram files from the corpus dir
        valid_files = []
        for f in self.fileids():
            m = re.search('(\w+)' + re.escape("-3grams.txt"), f)
            if m:
                valid_files.append( m.group() )
                
        for f in valid_files:
            ngram_file = self.root + '/' + f
            
            import os.path
            
            if os.path.isfile(ngram_file):
                crubadan_code = f.split('-')[0]
                iso_code = self.crubadan_to_iso(crubadan_code)

                fd = self.load_lang_ngrams(iso_code)
                self.all_lang_freq[iso_code] = fd
        
    def load_lang_ngrams(self, lang):
        ''' Load single n-gram language file given the ISO 639-3 language code
            and return its FreqDist '''
        
        crubadan_code = self.iso_to_crubadan(lang)
        ngram_file = self.root + '/' + unicode(crubadan_code) + '-3grams.txt'
        import os.path
        
        if not os.path.isfile(ngram_file):
            raise CrubadanError("Could not find language n-gram file for [" + lang + "].")

        counts = FreqDist()
            
        f = open(ngram_file, 'rU')
        
        for line in f:
            data = line.decode('utf-8').split(u' ')
            
            ngram = data[1].strip('\n')
            freq = int(data[0])
            
            counts[ngram] = freq
            
        return counts
    
    def lang_freq(self, lang):
        ''' Return n-gram FreqDist for a specific language
            given ISO 639-3 language code '''
        if len(self.all_lang_freq) == 0:
            return self.load_lang_ngrams(lang)
        else:
            return self.all_lang_freq[lang]
    
    def ngram_freq(self, lang, ngram):
        ''' Return n-gram frequency as integer given
            an ISO 639-3 language code and n-gram '''
        if lang not in self.all_lang_freq:
            raise CrubadanError("Unsupproted language [" + lang + "].")
            
        lf = self.all_lang_freq[lang]
        return lf[ngram]
        
    def supported_langs(self):
        ''' Return a list of supported languages in human-friendly form '''
        l = []
        for i in self._lang_mapping_data:
            l.append(i[2])
            
        return l
    
    def lang_supported(self, lang):
        ''' Check if a language is supported (language passed in as ISO 639-3 code) '''
        for i in self._lang_mapping_data:
            if i[1].lower() == lang.lower():
                return True
        
        return False

    def iso_to_friendly(self, lang):
        ''' Return human-friendly name for a lanuage based on ISO 639-3 code '''
        for i in self._lang_mapping_data:
            if i[1].lower() == lang.lower():
                return unicode(i[2])
        
        return None
    
    def friendly_to_iso(self, lang):
        ''' Return ISO 639-3 code from human-friendly language name (eg: "English" -> "en") '''
        for i in self._lang_mapping_data:
            if i[2].lower() == lang.lower():
                return unicode(i[1])
        
    def iso_to_crubadan(self, lang):
        ''' Return internal Crubadan code based on ISO 639-3 code '''
        for i in self._lang_mapping_data:
            if i[1].lower() == lang.lower():
                return unicode(i[0])
    
    def crubadan_to_iso(self, lang):
        ''' Return ISO 639-3 code given internal Crubadan code '''
        for i in self._lang_mapping_data:
            if i[0].lower() == lang.lower():
                return unicode(i[1])
    
    def _load_lang_mapping_data(self):
        ''' Load language mappings between codes and description from table.txt '''
        if isinstance(self.root, ZipFilePathPointer):
            raise CrubadanError("Please install the 'crubadan' corpus first, use nltk.download()")
        
        mapper_file = self.root + '/' + self._LANG_MAPPER_FILE
        if self._LANG_MAPPER_FILE not in self.fileids():
            raise CrubadanError("Could not find language mapper file [" + mapper_file + "].")
        
        f = open(mapper_file, 'rU')
        data = f.read().decode('utf-8').split('\n')
        for row in data:
            self._lang_mapping_data.append( row.split('\t') )
        
        # Get rid of empty entry if last line in file is blank
        if self._lang_mapping_data[ len(self._lang_mapping_data) - 1 ] == [u'']:
            self._lang_mapping_data.pop()

    def _is_utf8(self, str):
        ''' Check if a string is utf8 encoded '''
        try:
            str.decode('utf-8')
            return True
        except UnicodeError:
            return False
        
class CrubadanError(Exception):
    """An exception class for Crubadan n-gram reader related errors."""


