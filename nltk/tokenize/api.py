# Natural Language Toolkit: Tokenizer Interface
#
# Copyright (C) 2001-2010 NLTK Project
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

    # experimental
    def span_tokenize(self, s, relative=False):
        """
        Identify the tokens using integer offsets (start_i, end_i),
        where s[start_i:end_i] is the corresponding token.
        If relative=True, make each integer relative to the previous one.
        
        @return: C{iter} of C{tuple} of C{int}
        """
        raise NotImplementedError()

    def batch_tokenize(self, strings):
        """
        Apply L{self.tokenize()} to each element of C{strings}.  I.e.:

            >>> return [self.tokenize(s) for s in strings]

        @rtype: C{list} of C{list} of C{str}
        """
        return [self.tokenize(s) for s in strings]

    # experimental
    def batch_span_tokenize(self, strings, relative=False):
        """
        Apply L{self.span_tokenize()} to each element of C{strings}.  I.e.:

            >>> return [self.span_tokenize(s) for s in strings]

        @rtype: C{iter} of C{tuple} of C{int}
        """
        for s in strings:
            for span in self.span_tokenize(s):
                yield span


 