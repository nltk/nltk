# Natural Language Toolkit: Tokenizer Interface
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tokenizer Interface
"""
from nltk.internals import overridden
from util import string_span_tokenize

class TokenizerI(object):
    """
    A processing interface for I{tokenizing} a string, or dividing it
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

    def span_tokenize(self, s):
        """
        Identify the tokens using integer offsets (start_i, end_i),
        where s[start_i:end_i] is the corresponding token.
        
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

    def batch_span_tokenize(self, strings):
        """
        Apply L{self.span_tokenize()} to each element of C{strings}.  I.e.:

            >>> return [self.span_tokenize(s) for s in strings]

        @rtype: C{iter} of C{list} of C{tuple} of C{int}
        """
        for s in strings:
            yield list(self.span_tokenize(s))


class StringTokenizer(TokenizerI):
    r"""
    A tokenizer that divides a string into substrings by splitting
    on the specified string (defined in subclasses).
    """

    def tokenize(self, s):
        return s.split(self._string)
    
    def span_tokenize(self, s):
        for span in string_span_tokenize(s, self._string):
            yield span

