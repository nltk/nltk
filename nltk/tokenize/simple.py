# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
Tokenizers that divide strings into substrings using the string
``split()`` method.

These tokenizers implement the ``TokenizerI`` interface, and so
can be used with any code that expects a tokenizer, e.g.
:class:`~nltk.corpus.reader.CorpusReader`.

When tokenizing using a particular delimiter string, consider using
the string ``split()`` method directly, as this is more efficient.
"""

from .api import TokenizerI, StringTokenizer 
from .util import string_span_tokenize, regexp_span_tokenize
    
class SpaceTokenizer(StringTokenizer):
    """Tokenize a string using the space character as a delimiter.
    """

    _string = ' '
    
class TabTokenizer(StringTokenizer):
    """Tokenize a string use the tab character as a delimiter.
    """
    
    _string = '\t'
    
class CharTokenizer(StringTokenizer):
    """Tokenize a string into individual characters.  If this functionality
    is ever required directly, use ``for char in string``.
    """

    def tokenize(self, s):
        return list(s)

    def span_tokenize(self, s):
        for i, j in enumerate(range(1, len(s+1))):
            yield i, j
                              
class LineTokenizer(TokenizerI):
    """Tokenize a string into its lines, optionally discarding blank lines.
    """
    def __init__(self, blanklines='discard'):
        """
        :param blanklines: Indicates how blank lines should be
        handled.  Valid values are:
        
          - ``discard``: strip blank lines out of the token list
            before returning it.  A line is considered blank if
            it contains only whitespace characters.
          - ``keep``: leave all blank lines in the token list.
          - ``discard-eof``: if the string ends with a newline,
            then do not generate a corresponding token ``''`` after
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
