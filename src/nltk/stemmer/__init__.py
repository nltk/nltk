# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
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

##//////////////////////////////////////////////////////
##  Stemmer Interface
##//////////////////////////////////////////////////////

class StemmerI:
    """
    A processing interface for stemming strings.  Either single words
    or unrestricted text may be stemmed, producing the stemmed word or
    the text with each distinct word (whitespace separated) stemmed
    respectively.
    """

    def stem(self, token):
        """
        Remove any morphological affixes from the given word token.

        @param token: The word token that should be stemmed.
        @type token: C{token}
        @rtype: C{Token}
        @return: A new token whose type is the morphological stem of
            C{token.type()}, and whose location is C{token.loc()}.
        """
        raise AssertionError, 'StemmerI is an abstract interface'

## This function, or one much like it, will be included in a future
## version of this interface:
#    def stem_type(self, type):
#        """
#        Remove any morphological affixes from the given word type.
#
#        @param type: The word type that should be stemmed.  Typically,
#            C{type} is a C{string}; but depending on the stemmer, it
#            can be any immutable type.
#        @type type: any
#        @rtype: any
#        """
#        raise AssertionError, 'StemmerI is an abstract interface'
