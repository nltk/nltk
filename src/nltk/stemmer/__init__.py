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

C{StemmerI} defines an interface to which all stemmers must
adhere. This interface provides simple methods for stemming words.
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

    # The input and output properties that are used by most stemmers.
    # Specialized stemmers might add extra input properties or output
    # properties.
    _STANDARD_PROPERTIES = """
    @inprop: C{text}: The text content of the word to be stemmed.
    @outprop: C{stem}: The property where the stem should be stored.
    """
    __doc__ += _STANDARD_PROPERTIES

    def __init__(self, propnames={}):
        """
        Construct a new stemmer.

        @type propnames: C{dict}
        @param propnames: The names of the properties that are used by
            this stemmer.  These names are encoded as a dictionary
            that maps from abstract \"property specifications\" to
            concrete property names.  For a list of the property
            property specifications used by a particular stemmer, see
            its class docstring.
        """
        if self.__class__ == StemmerI:
            raise AssertionError, "Interfaces can't be instantiated"
        
    def stem(self, token):
        """
        Remove morphological affixes from given token's C{text}
        property, and write the remaining stem to the output property.

        @param token: The word token that should be stemmed.
        @type token: C{token}
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

class AbstractStemmer(StemmerI):
    """
    An abstract base class for stemmers that provides a default
    implementations for:
      - L{propnames}
      - L{stem} (based on C{raw_stem})
      
    @ivar _props: A dictionary from property specifications to
        property names, indicating which property names to use.
    """
    __doc__ += StemmerI._STANDARD_PROPERTIES
    
    def __init__(self, propnames={}):
        # Make sure we're not directly instantiated:
        if self.__class__ == AbstractStemmer:
            raise AssertionError, "Abstract classes can't eb instantiated"

        self._props = propnames

    def stem(self, token):
        assert chktype(1, token, Token)
        text_prop = self._props.get('text', 'text')
        stem_prop = self._props.get('stem', 'stem')
        token[stem_prop] = self.raw_stem(token[text_prop])

class RegexpStemmer(AbstractStemmer):
    """
    A stemmer that uses regular expressions to identify morphological
    affixes.  Any substrings that matches the regular expressions will
    be removed.
    """
    __doc__ += StemmerI._STANDARD_PROPERTIES
    
    def __init__(self, regexp, propnames={}):
        assert chktype(1, regexp, str)
        AbstractStemmer.__init__(self, propnames)
        if not hasattr(regexp, 'pattern'):
            regexp = re.compile(regexp)
        self._regexp = regexp

    def raw_stem(self, word):
        return self._regexp.sub('', word)

    def __repr__(self):
        return '<RegexpStemmer: %r>' % self._regexp.pattern

    def regexp(self):
        """
        @rtype: C{string}
        @return: The regular expression that is used to identify
        morphological affixes.
        """
        return self._regexp.pattern

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

    
