# Natural Language Toolkit: A Chunk Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A chunk parser is a kind of robust parser which identifies
linguistic groups (such as noun phrases) in unrestricted text,
typically one sentence at a time.  This task is sometimes called
X{chunking} the text, and the resulting text extents are called
X{chunks}.

Chunks are represented using X{chunk structures}, a list of lists.  If
M{t1...tn} are tokens, and M{[t1,...,tn]} is the input to a chunk
parser which identified M{tj...tk} as a chunk, the resulting chunk
structure would be M{[t1,...,tj-1,[tj,...tk],tk+1,tn]}.
"""

from nltk.token import TokenizerI, Token, Location
from nltk.chktype import chktype as _chktype
from nltk.tagger import parseTaggedType

from types import StringType as _StringType
import re

class ChunkParserI:
    """
    A processing interface for deriving chunk structures from a list of
    tokens.
    """
    def __init__(self):
        """
        Construct a new C{ChunkParser}.
        """

    def parse(self, tokens):
        """
        Parse the piece of text contained in the given list of
        tokens.  Return the chunk structure.
        
        @return: A chunk structure.
        @rtype: C{list} of (C{token} or (C{list} of C{token}))

        @param tokens: The list of tokens to be parsed.
        @type tokens: C{list} of C{token}
        """
        assert 0, "ChunkParserI is an abstract interface"

class ChunkedTaggedTokenizer(TokenizerI):
    """
    A tagged tokenizer that is sensitive to [] chunks, and returns a
    list of tokens and chunks, where each chunk is a list of tokens.

    n.b.: Strictly speaking, this is not a tokenizer!! (since it
    doesn't return a list of tokens)
    """
    def __init__(self): pass
    def tokenize(self, str, source=None):
        _chktype("ChunkedTaggedTokenizer.tokenize", 1, str, (_StringType,))

        # check that brackets are balanced and not nested
        brackets = re.sub(r'[^\[\]]', '', str)
        if not re.match(r'(\[\])*', brackets):
            print "ERROR: unbalanced or nested brackets"
            
        # Extract a list of alternating chinks & chunks
        pieces = re.split(r'[\[\]]', str)

        # Use this alternating list to create the chunklist.
        chunklist = []
        index = 0
        piece_in_chunk = 0
        for piece in pieces:
            # Convert the piece to a list of tokens.
            subsequence = []
            ttypes = [parseTaggedType(s) for s in piece.split()]
            for ttype in ttypes:
                loc = Location(index, unit='w', source=source)
                subsequence.append(Token(ttype, loc))
                index += 1
                
            # Add the list of tokens to our chunk list.
            if piece_in_chunk:
                chunklist.append(subsequence)
            else:
                chunklist += subsequence

            # Update piece_in_chunk
            piece_in_chunk = not piece_in_chunk

        return chunklist

