# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Interfaces used to remove morphological affixes from words, leaving only the
word stem. Stemming algorithms aim to remove those affixes required for
eg. grammatical role, tense, derivational morphology leaving only the stem of
the word. This is a difficult problem due to irregular words (eg. common verbs
in English), complicated morphological rules and part-of-speech and sense
ambiguities (eg. C{ceil-} is not the stem of C{ceiling}).

C{StemmerI} defines an interface to which all stemmers must adhere. This
interface provides simple methods for stemming words.

"""

##//////////////////////////////////////////////////////
##  Stemmer Interface
##//////////////////////////////////////////////////////

class StemmerI:
    """
    A processing interface for stemming strings.  Either single words or
    unrestricted text may be stemmed, producing the stemmed word or the text
    with each distinct word (whitespace separated) stemmed respectively.
    """
    def stem_word(self, word):
        """
        Stem a single word, returning a stemmed variant of the word.

        @return: the stemmed word.
        @rtype: C{string}
        @param word: the word to be stemmed.
        @type word: C{string}
        """
        raise AssertionError()
    
    def stem_text(self, text):
        """
        Stem a text consisting of many whitespace separated words. Each word
        will be stemmed and whitespace preserved. The stemmed text is
        returned.

        @return: the stemmed test.
        @rtype: C{string}
        @param word: the text to be stemmed.
        @type word: C{string}
        """
        raise AssertionError()

