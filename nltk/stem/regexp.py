# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re

from api import *

class RegexpStemmer(StemmerI):
    """
    A stemmer that uses regular expressions to identify morphological
    affixes.  Any substrings that match the regular expressions will
    be removed.
    """
    def __init__(self, regexp, min=0):
        """
        Create a new regexp stemmer.

        @type regexp: C{string} or C{regexp}
        @param regexp: The regular expression that should be used to
            identify morphological affixes.
        @type min: int
        @param min: The minimum length of string to stem
        """

        if not hasattr(regexp, 'pattern'):
            regexp = re.compile(regexp)
        self._regexp = regexp
        self._min = min

    def stem(self, word):
        if len(word) < self._min:
            return word
        else:
            return self._regexp.sub('', word)

    def __repr__(self):
        return '<RegexpStemmer: %r>' % self._regexp.pattern

def demo():
    from nltk import tokenize, stem

    # Create a simple regular expression based stemmer
    stemmer = stem.RegexpStemmer('ing$|s$|e$', min=4)
    text = "John was eating icecream"
    tokens = text.split()

    # Print the results.
    print stemmer
    for word in tokens:
        print '%20s => %s' % (word, stemmer.stem(word))
    print
        

if __name__ == '__main__': demo()

    
