# Natural Language Toolkit: Token Readers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes for reading string representations of tokens.
"""

from nltk import TaskI
from nltk.token import *

######################################################################
## Token Reader Interface
######################################################################

class TokenReaderI(TaskI):
    # [XX] This docstring isn't as clear as I'd like:
    """
    An interface for parsing string representations of tokens.
    Different token readers can be used to parse different string
    representations.  The tokens returned by a token reader should
    contain all of the information encoded in the string
    representation; but this information may be different for
    different representations.  I.e., different token readers will
    return tokens that define different properties.
    """
    def read_token(s):
        """
        @return: The token encoded by the string C{s}.
        @rtype: L{Token}
        """
        raise NotImplementedError
    def read_tokens(s):
        """
        @return: A list of the tokens encoded by the string C{s}.
        @rtype: C{list} of L{Token}
        """
        raise NotImplementedError

######################################################################
## Tokenzier-based token readers
######################################################################

class TokenizerBasedTokenReader(TokenReaderI):
    def __init__(self, tokenizer):
        self._tokenizer = tokenizer

    def read_token(self, s, *tokenizer_args, **tokenizer_kwargs):
        """
        @param tokenizer_args, tokenizer_kwargs: Arguments that are
        passed on to the tokenizer's C{tokenize} method.
        """
        TEXT = self.property('TEXT')
        SUBTOKENS = self.property('SUBTOKENS')
        tok = Token(**{TEXT: s})
        if 'source' in tokenizer_kwargs:
            tok['LOC'] = tokenizer_kwargs['source']
            del tokenizer_kwargs['source']
        self._tokenizer.tokenize(tok, *tokenizer_args, **tokenizer_kwargs)
        del tok[TEXT]
        return tok
                         
    def read_tokens(self, s, *tokenizer_args, **tokenizer_kwargs):
        """
        @param tokenizer_args, tokenizer_kwargs: Arguments that are
        passed on to the tokenizer's C{tokenize} method.
        """
        return [self.read_token(s, *tokenizer_args, **tokenizer_kwargs)]

    def property(self, property):
        return self._tokenizer.property(property)

class WhitespaceSeparatedTokenReader(TokenizerBasedTokenReader):
    """
    A token reader that reads in tokens that are stored as simple
    strings, separated by whitespace.  Individual tokens may not
    contain internal whitespace.

        >>> reader = WhitespaceSeparatedTokenReader(SUBTOKENS='WORDS')
        >>> print reader.read_tokens('tokens separated by spaces')
        [<tokens>, <separated>, <by>, <spaces>]
    """
    def __init__(self, **property_names):
        from nltk.tokenizer import WhitespaceTokenizer
        tokenizer = WhitespaceTokenizer(**property_names)
        TokenizerBasedTokenReader.__init__(self, tokenizer)
        
class NewlineSeparatedTokenReader(TokenizerBasedTokenReader):
    """
    A token reader that reads in tokens that are stored as simple
    strings, separated by newlines.  Blank lines are ignored.

        >>> reader = NewlineSeparatedTokenReader(SUBTOKENS='WORDS')
        >>> print reader.read_tokens('tokens\nseparated\nby\n\nnewlines')
        [<tokens>, <separated>, <by>, <newlines>]
    """
    def __init__(self, **property_names):
        from nltk.tokenizer import LineTokenizer
        tokenizer = LineTokenizer(**property_names)
        TokenizerBasedTokenReader.__init__(self, tokenizer)
        
######################################################################
## Import other token readers
######################################################################

from nltk.tokenreader.treebank import *
from nltk.tokenreader.tagged import *
from nltk.tokenreader.conll import *
from nltk.tokenreader.ieer import *

######################################################################
## Demo
######################################################################

def demo():
    print 'Whitespace separated token reader:'
    reader = WhitespaceSeparatedTokenReader(SUBTOKENS='WORDS')
    print reader.read_tokens('tokens separated by spaces', add_locs=True)

    print 'Newline separated token reader:'
    reader = NewlineSeparatedTokenReader(SUBTOKENS='WORDS')
    print reader.read_tokens('tokens\nseparated\nby\n\nnewlines')

if __name__ == '__main__':
    demo()
