# Natural Language Toolkit: Wordnet Interface: Sense frequency
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

# Count of a tagged sense in a semantic concordance

import types

import nltk.data

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
        line = binarySearchFile(self._file, key)
        if line:
            return int(line.rsplit(' ', 1)[-1])

senseCount = SenseCount()
