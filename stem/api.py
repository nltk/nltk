# Natural Language Toolkit: Stemmer Interface
#
# Copyright (C) 2001-2007 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

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

