# Natural Language Toolkit: WordNet stemmer
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Temporary(?) resting place for the WordNet based stemmer.
"""

from nltk.stemmer import StemmerI
from nltk.token import Token
from nltk_contrib.pywordnet.tools import morphy

##//////////////////////////////////////////////////////
##  WordNet Stemmer
##//////////////////////////////////////////////////////

class WordNetStemmer(StemmerI):
    """
    A class for stemming strings using the pywordnet package. The C{morphy}
    function is used which reduces the given word form into a word which
    exists in the WordNet database, if possible. Note that morphological
    affixes often remain after stemming, as WordNet contains quite a number of
    entries for inflectional forms. This stemmer is not as powerful as the one
    contained in the C{wnb} binary distributed with WordNet 1.7 - there are
    plans to improve this in the near future.
    """

    def stem(self, token):
        # inherit docs from StemmerI
        stemmed = morphy(token.type().lower())
        if stemmed:
            # restore the case
            new_string = ''
            for index in range(min(len(token.type()), len(stemmed))):
                if token.type()[index].isupper():
                    new_string += stemmed[index].upper()
                else:
                    new_string += stemmed[index]
            return Token(new_string, token.loc())
        else:
            return token

