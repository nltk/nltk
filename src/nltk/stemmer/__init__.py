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
    """
    def stem(self, token, **propnames):
        """
        Remove morphological affixes from given token's C{text}
        property, and output the remaining stem to the C{stem}
        property.

        @param token: The word token that should be stemmed.
        @type token: L{Token}
        @type propnames: C{dict}
        @param propnames: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        @inprop: C{text}: The text content of the word to be stemmed.
        @outprop: C{stem}: The property where the stem should be
                  stored.
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

    def stem_n(self, token, n=None, **propnames):
        """
        Find a list of the C{n} most likely stems for the given token,
        and output it to the C{stems} property.  If the given token
        has fewer than C{n} possible stems, then find all possible
        stems.  The stems should be sorted in descending order of
        estimated likelihood.

        @param token: The word token that should be stemmed.
        @type token: L{Token}
        @param n: The maximum number of stems to generate.  If C{n}
            is C{None}, then generate all possible stems.
        @param propnames: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        @inprop: C{text}: The text content of the word to be stemmed.
        @outprop: C{stems}: The property where the list of stems
                  should be stored.
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
    """
    def __init__(self):
        # Make sure we're not directly instantiated:
        if self.__class__ == AbstractStemmer:
            raise AssertionError, "Abstract classes can't be instantiated"

    def raw_stem(self, text):
      token = Token(text=text)
      self.stem(token)
      return token['stem']

    def stem_n(self, token, n=None, **propnames):
      stems_prop = propnames.get('stem', 'stem')
      if n == 0:
          token[stems_prop] = []   # (pathological case)
      else:
          self.stem(token)
          token[stems_prop] = [token['stem']]
      del token['stem']

    def raw_stem_n(self, text, n=None):
        token = Token(text=text)
        self.stem_n(token, n)
        return token['stems']

    def _stem_from_raw(self, token, **propnames):
        text_prop = propnames.get('text', 'text')
        stem_prop = propnames.get('stem', 'stem')
        token[stem_prop] = self.raw_stem(token[text_prop])

    def _stem_n_from_raw(self, token, **propnames):
        text_prop = propnames.get('text', 'text')
        stems_prop = propnames.get('stems', 'stems')
        token[stems_prop] = self.raw_stem_n(token[text_prop])

class RegexpStemmer(AbstractStemmer):
    """
    A stemmer that uses regular expressions to identify morphological
    affixes.  Any substrings that matches the regular expressions will
    be removed.
    """
    def __init__(self, regexp):
        assert chktype(1, regexp, str)
        if not hasattr(regexp, 'pattern'):
            regexp = re.compile(regexp)
        self._regexp = regexp

    def raw_stem(self, word):
        return self._regexp.sub('', word)

    def stem(self, token, **propnames):
        # Delegate to self.raw_stem()
        return self._stem_from_raw(token, **propnames)

    def __repr__(self):
        return '<RegexpStemmer: %r>' % self._regexp.pattern

def _demo_stemmer(stemmer):
    # Tokenize a sample text.
    from nltk.tokenizer import WSTokenizer
    text = Token(text='John was eating icecream')
    WSTokenizer(addlocs=False).tokenize(text)

    # Use the stemmer to stem it.
    for word in text['subtokens']: stemmer.stem(word)

    # Print the results.
    print stemmer
    for word in text['subtokens']:
        print '%20s => %s' % (word['text'], word['stem'])
    print
        
def demo():
    # Create a simple regular expression based stemmer
    stemmer = RegexpStemmer('ing$|s$|e$')
    _demo_stemmer(stemmer)

    from nltk.stemmer.porter import PorterStemmer
    stemmer = PorterStemmer()
    _demo_stemmer(stemmer)

if __name__ == '__main__': demo()

    
