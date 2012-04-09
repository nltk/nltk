# Natural Language Toolkit: WordNet stemmer interface
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.wordnet import NOUN
from nltk.corpus import wordnet

class WordNetLemmatizer(object):
    """
    WordNet Lemmatizer

    Lemmatize using WordNet's built-in morphy function.
    Returns the input word unchanged if it cannot be found in WordNet.

        >>> from nltk.stem import WordNetLemmatizer
        >>> wnl = WordNetLemmatizer()
        >>> wnl.lemmatize('dogs')
        'dog'
        >>> wnl.lemmatize('churches')
        'church'
        >>> wnl.lemmatize('aardwolves')
        'aardwolf'
        >>> wnl.lemmatize('abaci')
        'abacus'
        >>> wnl.lemmatize('hardrock')
        'hardrock'
    """

    def __init__(self):
        pass

    def lemmatize(self, word, pos=NOUN):
        lemmas = wordnet._morphy(word, pos)
        return min(lemmas, key=len) if lemmas else word

    def __repr__(self):
        return '<WordNetLemmatizer>'


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
