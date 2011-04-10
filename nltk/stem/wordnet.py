# Natural Language Toolkit: WordNet stemmer interface
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.wordnet import NOUN
from nltk.corpus import wordnet as _wordnet

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
        lemmas = _wordnet._morphy(word, pos)
        if not lemmas:
            return word
        lemmas.sort(key=len)
        return lemmas[0]

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
