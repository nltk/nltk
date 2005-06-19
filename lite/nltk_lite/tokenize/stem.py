# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2001-2005 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu> (rewrite)
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Interfaces used to remove morphological affixes from words, leaving
only the word stem.  Stemming algorithms aim to remove those affixes
required for eg. grammatical role, tense, derivational morphology
leaving only the stem of the word.  This is a difficult problem due to
irregular words (eg. common verbs in English), complicated
morphological rules, and part-of-speech and sense ambiguities
(eg. C{ceil-} is not the stem of C{ceiling}).

C{StemmerI} defines a standard interface for stemmers.
"""

import re

##//////////////////////////////////////////////////////
##  Stemmer Interface
##//////////////////////////////////////////////////////

class StemmerI:
    """
    A processing interface for removing morphological affixes from
    words.  This process is known as X{stemming}.
    
    """
    def stem(self, token):
        """
        Strip affixes from the token and return the stem.

        @param token: The token that should be stemmed.
        @type token: L{string}
        """
        raise NotImplementedError()

class RegexpStemmer(StemmerI):
    """
    A stemmer that uses regular expressions to identify morphological
    affixes.  Any substrings that matches the regular expressions will
    be removed.
    """
    def __init__(self, regexp):
        """
        Create a new regexp stemmer.

        @type regexp: C{string} or C{regexp}
        @param regexp: The regular expression that should be used to
            identify morphological affixes.
        """

        if not hasattr(regexp, 'pattern'):
            regexp = re.compile(regexp)
        self._regexp = regexp

    def stem(self, word):
        return self._regexp.sub('', word)

    def __repr__(self):
        return '<RegexpStemmer: %r>' % self._regexp.pattern

def _demo_stemmer(stemmer):
    # Tokenize a sample text.
    from nltk_lite import tokenize
    text = "John was eating icecream"
    tokens = tokenize.whitespace(text)

    # Print the results.
    print stemmer
    for word in tokens:
        print '%20s => %s' % (word, stemmer.stem(word))
    print
        
def demo():
    # Create a simple regular expression based stemmer
    stemmer = RegexpStemmer('ing$|s$|e$')
    _demo_stemmer(stemmer)

#    from porter import PorterStemmer
#    stemmer = PorterStemmer()
#    _demo_stemmer(stemmer)

if __name__ == '__main__': demo()

    
