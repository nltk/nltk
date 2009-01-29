# Natural Language Toolkit: Tokenizer Interface
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tokenizer Interface
"""
from nltk.internals import overridden

class TokenizerI(object):
    """
    A procesing interface for I{tokenizing} a string, or dividing it
    into a list of substrings.
    
    Subclasses must define:
      - either L{tokenize()} or L{batch_tokenize()} (or both)
    """
    def tokenize(self, s):
        """
        Divide the given string into a list of substrings.
        
        @return: C{list} of C{str}
        """
        if overridden(self.batch_tokenize):
            return self.batch_tokenize([s])[0]
        else:
            raise NotImplementedError()

    def batch_tokenize(self, strings):
        """
        Apply L{self.tokenize()} to each element of C{strings}.  I.e.:

            >>> return [self.tokenize(s) for s in strings]

        @rtype: C{list} of C{list} of C{str}
        """
        return [self.tokenize(s) for s in strings]
