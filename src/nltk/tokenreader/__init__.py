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

######################################################################
## Token Reader Interface
######################################################################

# Note that this is not a subclass of TaskI: It takes strings as
# inputs, not tokens; and it's just doing deterministic parsing, not a
# real natural language processing task.
class TokenReaderI:
    # [XX] This docstring isn't as clear as I'd like:
    """
    An interface for parsing string representations of tokens.
    Different token readers can be used to parse different string
    representations.  The tokens returned by a token reader should
    contain all of the information encoded in the string
    representation; but this information may be different for
    different representations.  I.e., different token readers will
    return tokens that define different properties.

    Many token readers define additional arguments to C{read_token}
    and C{read_tokens}, such as C{add_locs}, C{add_context},
    C{add_subtoks}, and C{add_text}, which control exactly which
    properties are recorded when the token is read.  See each
    individual token reader's C{read_token} documentation for
    information about any additional arguments it supports.
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
## Import token reader implementations.
######################################################################

from nltk.tokenreader.tokenizerbased import *
from nltk.tokenreader.treebank import *
from nltk.tokenreader.tagged import *
from nltk.tokenreader.conll import *
from nltk.tokenreader.ieer import *
from nltk.tokenreader.sense import *

######################################################################
## Demo
######################################################################

def demo():
    print 'Whitespace separated token reader:'
    reader = WhitespaceSeparatedTokenReader(SUBTOKENS='WORDS')
    print reader.read_token('tokens separated by spaces', add_locs=True)

    print 'Newline separated token reader:'
    reader = NewlineSeparatedTokenReader(SUBTOKENS='WORDS')
    print reader.read_token('tokens\nseparated\nby\n\nnewlines')

    print 'Treebank token reader:'
    reader = TreebankTokenReader(SUBTOKENS='WORDS', add_subtoks=False)
    print reader.read_token('(DP (DET a) (NP (NN Treebank) (NN Tree)))')

if __name__ == '__main__':
    demo()
