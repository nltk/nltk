# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu> (rewrite)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

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

from nltk.chktype import chktype
from nltk.token import Token
import re

##//////////////////////////////////////////////////////
##  Stemmer Interface
##//////////////////////////////////////////////////////

class StemmerI:
    """
    A processing interface for removing morphological affixes from
    words.  This process is known as X{stemming}.
    
    @outprop: C{STEM}: The token's morphological stem.
    """
    def stem(self, token):
        """
        Remove morphological affixes from given token's C{TEXT}
        property, and output the remaining stem to the C{STEM}
        property.

        @param token: The word token that should be stemmed.
        @type token: L{Token}
        """
        raise NotImplementedError()

    def raw_stem(self, word):
        """
        Remove morphological affixes from the given word string, and
        return the resulting stem.

        @param word: The word to be stemmed.
        @type word: C{string}
        @rtype: C{string}
        """
        raise NotImplementedError()

    def stem_n(self, token, n=None):
        """
        Find a list of the C{n} most likely stems for the given token,
        and output it to the C{STEMS} property.  If the given token
        has fewer than C{n} possible stems, then find all possible
        stems.  The stems should be sorted in descending order of
        estimated likelihood.

        @param token: The word token that should be stemmed.
        @type token: L{Token}
        @param n: The maximum number of stems to generate.  If C{n}
            is C{None}, then generate all possible stems.
        """
        raise NotImplementedError()

    def raw_stem_n(self, word, n=None):
        """
        @return: A list of the C{n} most likely stems for the given
        word string.  If the given word string has fewer than C{n}
        possible stems, then return all possible stems.  The stems
        should be sorted in descending order of estimated likelihood.

        @param word: The word to be stemmed.
        @type word: C{string}
        @param n: The maximum number of stems to generate.  If C{n}
            is C{None}, then generate all possible stems.
        """
        raise NotImplementedError()

class AbstractStemmer(StemmerI):
    """
    An abstract base class for stemmers.  C{AbstractStemmer} provides
    a default implementations for:

      - L{raw_stem} (based on C{stem})
      - L{stem_n} (based on C{stem})
      - L{raw_stem_n} (based on C{stem_n})

    It also provides L{_stem_from_raw}, which can be used to implement
    C{stem} based on C{raw_stem}; and L{stem_n_from_raw}, which can be
    used to implement C{stem_n} based on C{raw_stem_n}.
    
    @inprop: C{STEM}: The token's text content.
    @outprop: C{STEM}: The token's morphological stem.
    """
    def __init__(self, **property_names):
        """
        Create a new stemmer.
        
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        # Make sure we're not directly instantiated:
        if self.__class__ == AbstractStemmer:
            raise AssertionError, "Abstract classes can't be instantiated"
        self._property_names = property_names

    def raw_stem(self, text):
        TEXT = self._property_names.get('TEXT', 'TEXT')
        STEM = self._property_names.get('STEM', 'STEM')
        token = Token({TEXT:text})
        self.stem(token)
        return token[STEM]

    def stem_n(self, token, n=None):
        STEMS = self._property_names.get('STEMS', 'STEMS')
        STEM = self._property_names.get('STEM', 'STEM')
        if n == 0:
            token[STEMS] = []   # (pathological case)
        else:
            self.stem(token)
            token[STEMS] = [token[STEM]]
        del token[STEM]

    def raw_stem_n(self, text, n=None):
        TEXT = self._property_names.get('TEXT', 'TEXT')
        STEM = self._property_names.get('STEM', 'STEM')
        token = Token({TEXT:text})
        self.stem_n(token, n)
        return token[STEM]

    def _stem_from_raw(self, token):
        TEXT = self._property_names.get('TEXT', 'TEXT')
        STEM = self._property_names.get('STEM', 'STEM')
        token[STEM] = self.raw_stem(token[TEXT])

    def _stem_n_from_raw(self, token):
        TEXT = self._property_names.get('TEXT', 'TEXT')
        STEMS = self._property_names.get('STEMS', 'STEMS')
        token[STEMS] = self.raw_stem_n(token[TEXT])

class RegexpStemmer(AbstractStemmer):
    """
    A stemmer that uses regular expressions to identify morphological
    affixes.  Any substrings that matches the regular expressions will
    be removed.
    
    @inprop: C{STEM}: The token's text content.
    @outprop: C{STEM}: The token's morphological stem.
    """
    def __init__(self, regexp, **property_names):
        """
        Create a new regexp stemmer.

        @type regexp: C{string} or C{regexp}
        @param regexp: The regular expression that should be used to
            identify morphological affixes.
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        if not hasattr(regexp, 'pattern'):
            regexp = re.compile(regexp)
        self._regexp = regexp
        AbstractStemmer.__init__(self, **property_names)

    def raw_stem(self, word):
        return self._regexp.sub('', word)

    def stem(self, token):
        # Delegate to self.raw_stem()
        return self._stem_from_raw(token)

    def __repr__(self):
        return '<RegexpStemmer: %r>' % self._regexp.pattern

def _demo_stemmer(stemmer):
    # Tokenize a sample text.
    from nltk.tokenizer import WSTokenizer
    text = Token(TEXT='John was eating icecream')
    WSTokenizer(addlocs=False).tokenize(text)

    # Use the stemmer to stem it.
    for word in text['SUBTOKENS']: stemmer.stem(word)

    # Print the results.
    print stemmer
    for word in text['SUBTOKENS']:
        print '%20s => %s' % (word['TEXT'], word['STEM'])
    print
        
def demo():
    # Create a simple regular expression based stemmer
    stemmer = RegexpStemmer('ing$|s$|e$')
    _demo_stemmer(stemmer)

    from nltk.stemmer.porter import PorterStemmer
    stemmer = PorterStemmer()
    _demo_stemmer(stemmer)

if __name__ == '__main__': demo()

    
