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

    def propnames(self):
        """
        @rtype: C{dict}
        @return: The names of the properties that are used by this
        tokenizer.  These names are encoded as a dictionary that maps
        from abstract \"property specifications\" to concrete property
        names.  For a list of the property specifications used by a
        particular tokenizer, see its class docstring.
        """
        raise NotImplementedError()

class AbstractStemmer(StemmerI):
    """
    An abstract base class for stemmers that provides a default
    implementations for:
      - L{propnames}
      - L{stem} (based on C{raw_stem})
      
    @ivar _propnames: A dictionary from property specifications to
        property names, indicating which property names to use.
    """
    __doc__ += StemmerI._STANDARD_PROPERTIES
    
    def __init__(self, propnames={}):
        # Make sure we're not directly instantiated:
        if self.__class__ == AbstractStemmer:
            raise AssertionError, "Abstract classes can't eb instantiated"

        self._propnames = propnames

    def propnames(self):
        # Inherit docs from StemmerI
        return self._propnames.copy()

    def stem(self, token):
        # Inherit docs from StemmerI
        assert chktype(1, token, Token)
        text_pname = self._propnames.get('text', 'text')
        stem_pname = self._propnames.get('stem', 'stem')
        token[stem_pname] = self.raw_stem(token[text_pname])

class REStemmer(AbstractStemmer):
    """
    A stemmer that uses a regular expression to identify morphological
    affixes.  Any substrings that matche the regular expression will
    be removed.
    """
    __doc__ += StemmerI._STANDARD_PROPERTIES
    
    def __init__(self, regexp, propnames={}):
        # Inherit docs from StemmerI
        assert chktype(1, regexp, str)
        AbstractStemmer.__init__(self, propnames)
        self._regexp = re.compile(regexp)

    def raw_stem(self, word):
        # Inherit docs from StemmerI
        return self._regexp.sub('', word)
    
