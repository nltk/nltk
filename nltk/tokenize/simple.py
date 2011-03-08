# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Trevor Cohn <tacohn@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
Tokenizers that divide strings into substrings using the string
C{split()} method.

These tokenizers follow the standard L{TokenizerI} interface, and so
can be used with any code that expects a tokenizer.  For example,
these tokenizers can be used to specify the tokenization conventions
when building a L{CorpusReader<nltk.corpus.reader.api.CorpusReader>}.
But if you are tokenizing a string yourself, consider using string
C{split()} method directly instead.
"""

from api import *
from util import *
    
class SpaceTokenizer(StringTokenizer):
    r"""
    A tokenizer that divides a string into substrings by treating any
    single space character as a separator.  If you are performing the
    tokenization yourself (rather than building a tokenizer to pass to
    some other piece of code), consider using the string C{split()}
    method instead:

        >>> words = s.split(' ')
    """

    _string = ' '
    
class TabTokenizer(StringTokenizer):
    r"""
    A tokenizer that divides a string into substrings by treating any
    single tab character as a separator.  If you are performing the
    tokenization yourself (rather than building a tokenizer to pass to
    some other piece of code), consider using the string C{split()}
    method instead:

        >>> words = s.split('\t')
    """
    
    _string = '\t'
    
class CharTokenizer(StringTokenizer):
    r"""
    A tokenizer that produces individual characters.  If you are performing
    the tokenization yourself (rather than building a tokenizer to pass to
    some other piece of code), consider iterating over the characters of
    the string directly instead: for char in string
    """

    def tokenize(self, s):
        return list(s)

    def span_tokenize(self, s):
        for i, j in enumerate(range(1, len(s+1))):
            yield i, j
                              
class LineTokenizer(TokenizerI):
    r"""
    A tokenizer that divides a string into substrings by treating any
    single newline character as a separator.  Handling of blank lines
    may be controlled using a constructor parameter.
    """
    def __init__(self, blanklines='discard'):
        """
        @param blanklines: Indicates how blank lines should be
        handled.  Valid values are:
        
          - C{'discard'}: strip blank lines out of the token list
            before returning it.  A line is considered blank if
            it contains only whitespace characters.
          - C{'keep'}: leave all blank lines in the token list.
          - C{'discard-eof'}: if the string ends with a newline,
            then do not generate a corresponding token C{''} after
            that newline.
        """
        valid_blanklines = ('discard', 'keep', 'discard-eof')
        if blanklines not in valid_blanklines:
            raise ValueError('Blank lines must be one of: %s' %
                             ' '.join(valid_blanklines))
            
        self._blanklines = blanklines
    
    def tokenize(self, s):
        lines = s.splitlines()
        # If requested, strip off blank lines.
        if self._blanklines == 'discard':
            lines = [l for l in lines if l.rstrip()]
        elif self._blanklines == 'discard-eof':
            if lines and not lines[-1].strip(): lines.pop()
        return lines

    # discard-eof not implemented
    def span_tokenize(self, s):
        if self._blanklines == 'keep':
            for span in string_span_tokenize(s, r'\n'):
                yield span
        else:
            for span in regexp_span_tokenize(s, r'\n(\s+\n)*'):
                yield span

######################################################################
#{ Tokenization Functions
######################################################################

def line_tokenize(text, blanklines='discard'):
    return LineTokenizer(blanklines).tokenize(text)
