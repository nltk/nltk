# Natural Language Toolkit: Wordnet Interface: Sense frequency
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Count of a tagged sense in a semantic concordance

# Incomplete:
# work out how to construct key
# access method for individual wordsense, e.g. N['dog'][0].count()

import types
from util import *
import nltk.data

class SenseCount(object):
    
    def __init__(self):
        self._loaded = False
        
    def load(self):
        if not self._loaded:
            path = nltk.data.find('corpora/wordnet/cntlist.rev')
            self._file = open(path, FILE_OPEN_MODE)
            self._loaded = True
    
    def count(self, key):
        self.load()
        line = binarySearchFile(self._file, key)
        # incomplete

S = SenseCount()
