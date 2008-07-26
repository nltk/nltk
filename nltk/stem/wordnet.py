# Natural Language Toolkit: Wordnet stemmer interface
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.wordnet import morphy

from api import *

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

