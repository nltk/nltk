# Natural Language Toolkit: Taggers
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

Chunks are represented using "chunk structures", a list of lists.  If
t1...tn are tokens, and [t1,...,tn] is the input to a chunk parser
which identified tj...tk as a chunk, the resulting chunk structure
would be [t1,...,tj-1,[tj,...tk],tk+1,tn].
"""

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

