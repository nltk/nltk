# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2001-2006 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
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

C{StemI} defines a standard interface for stemmers.
"""

import re

##//////////////////////////////////////////////////////
##  Stemmer Interface
##//////////////////////////////////////////////////////

class StemI(object):
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


from regexp import *
from porter import *
