# Natural Language Toolkit: Stemmer Interface
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

class StemmerI(object):
    """
    A processing interface for removing morphological affixes from
    words.  This process is known as stemming.

    """
    def stem(self, token):
        """
        Strip affixes from the token and return the stem.

        :param token: The token that should be stemmed.
        :type token: str
        """
        raise NotImplementedError()


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
