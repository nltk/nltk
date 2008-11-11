# Natural Language Toolkit: WordNet stemmer interface
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.corpus import wordnet
from nltk.internals import Deprecated

from api import *

class WordNetStemmer(StemmerI):
    """
    A stemmer that uses WordNet's built-in morphy function.
    """
    def __init__(self):
        """
        Create a new WordNet stemmer.
        """
        pass

    def stem(self, word, pos=wordnet.NOUN):
        
        word_stem = wordnet.morphy(word, pos) 
        if not word_stem:
            word_stem = word
        return word_stem

    def __repr__(self):
        return '<WordNetStemmer>'

if __name__ == '__main__':
    from nltk import stem
    stemmer = stem.WordNetStemmer()
    print 'dogs ->', stemmer.stem('dogs')
    print 'churches ->', stemmer.stem('churches')
    print 'aardwolves ->', stemmer.stem('aardwolves')
    print 'abaci ->', stemmer.stem('abaci')
    print 'hardrock ->', stemmer.stem('hardrock')

class WordnetStemmer(Deprecated, WordNetStemmer):
    """Use WordNetStemmer instead."""
    def __init__(self):
        WordNetStemmer.__init__(self)
