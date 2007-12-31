# Natural Language Toolkit: Wordnet stemmer interface
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from api import *
from nltk.wordnet import morphy

class WordnetStemmer(StemmerI):
    """
    A stemmer that uses Wordnet's built-in morphy function.
    """
    def __init__(self):
        """
        Create a new wordnet stemmer.
        """
        pass

    def stem(self, word):
        return morphy(word)

    def __repr__(self):
        return '<WordnetStemmer>'

if __name__ == '__main__':
    from nltk import stem
    stemmer = stem.WordnetStemmer()
    print 'dogs ->', stemmer.stem('dogs')
    print 'churches ->', stemmer.stem('churches')
    print 'aardwolves ->', stemmer.stem('aardwolves')
    print 'abaci ->', stemmer.stem('abaci')
    print 'hardrock ->', stemmer.stem('hardrock')

