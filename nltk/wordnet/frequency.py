# Natural Language Toolkit: Wordnet Interface: Sense frequency
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

# Count of a tagged sense in a semantic concordance

import types

import nltk.data
from nltk.util import binary_search_file

from util import *

class SenseCount(object):
    
    def __init__(self):
        self._loaded = False
        
    def load(self):
        if not self._loaded:
            path = nltk.data.find('corpora/wordnet/cntlist.rev')
            self._file = open(path, FILE_OPEN_MODE)
            self._loaded = True
    
    def __call__(self, key):
        self.load()
        line = binary_search_file(self._file, key)
        if line:
            return int(line.rsplit(' ', 1)[-1])

senseCount = SenseCount()
