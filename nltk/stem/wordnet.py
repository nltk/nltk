# Natural Language Toolkit: WordNet stemmer interface
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.wordnet import NOUN
from nltk.corpus import wordnet as _wordnet
from nltk.internals import Deprecated

class WordNetLemmatizer(object):
    """
    A lemmatizer that uses WordNet's built-in morphy function.
    """
    def __init__(self):
        """
        Create a new WordNet stemmer.
        """
        pass

    def lemmatize(self, word, pos=NOUN):
        
        lemma = _wordnet.morphy(word, pos) 
        if not lemma:
            lemma = word
        return lemma

    def __repr__(self):
        return '<WordNetLemmatizer>'

if __name__ == '__main__':
    from nltk import stem
    wnl = stem.WordNetLemmatizer()
    print 'dogs ->', wnl.lemmatize('dogs')
    print 'churches ->', wnl.lemmatize('churches')
    print 'aardwolves ->', wnl.lemmatize('aardwolves')
    print 'abaci ->', wnl.lemmatize('abaci')
    print 'hardrock ->', wnl.lemmatize('hardrock')

class WordnetStemmer(Deprecated, WordNetLemmatizer):
    """Use WordNetLemmatizer instead."""
    def __init__(self):
        WordNetLemmatizer.__init__(self)

class WordNetStemmer(Deprecated, WordNetLemmatizer):
    """Use WordNetLemmatizer instead."""
    def __init__(self):
        WordNetLemmatizer.__init__(self)


