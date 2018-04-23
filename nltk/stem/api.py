# Natural Language Toolkit: Stemmer Interface
#
# Copyright (C) 2001-2018 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class StemmerI(object):
    """
    A processing interface for removing morphological affixes from
    words.  This process is known as stemming.

    """
    @abstractmethod
    def stem(self, token):
        """
        Strip affixes from the token and return the stem.

        :param token: The token that should be stemmed.
        :type token: str
        """
