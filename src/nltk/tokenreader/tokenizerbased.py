# Natural Language Toolkit: Tokenizer-Based Token Readers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Token readers whose behavior is based on tokenizers.
"""

class TokenizerBasedTokenReader(TokenReaderI, PropertyIndirectionI):
    """
    A token reader whose behavior is based on a given tokenizer.  This
    token reader uses the given tokenizer to split the string into
    subtokens, and creates a single token out of those subtokens.
    """
    def __init__(self, tokenizer):
        """
        Create a new token reader, based on the given tokenizer.
        
        @param tokenizer: The tokenizer that will be used to split
            input strings into subtokens.
        @type tokenizer: L{TokenizerI}
        """
        self._tokenizer = tokenizer

    def read_token(self, s, add_text=False,
                   *tokenizer_args, **tokenizer_kwargs):
        """
        @return: The token encoded by the string C{s}.
        @rtype: L{Token}
        @param add_text: If true, then include the input string C{s}
            in the output token's C{TEXT} property; otherwise, discard
            it.
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
        if not add_text:
            del tok[TEXT]
        return tok
                         
    def read_tokens(self, s, *tokenizer_args, **tokenizer_kwargs):
        """
        @return: A list of the tokens encoded by the string C{s}.
            This list will contain the single token returned by
            C{read_token(s)}.
        @rtype: C{list} of L{Token}
        @param add_text: If true, then include the input string C{s}
            in the output token's C{TEXT} property; otherwise, discard
            it.
        @param tokenizer_args, tokenizer_kwargs: Arguments that are
            passed on to the tokenizer's C{tokenize} method.
        """
        return [self.read_token(s, *tokenizer_args, **tokenizer_kwargs)]

    def property(self, property):
        return self._tokenizer.property(property)
    def property_names(self):
        return self._tokenizer.property_names()

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
        
