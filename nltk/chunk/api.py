# Natural Language Toolkit: Chunk parsing API
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

##//////////////////////////////////////////////////////
##  Chunk Parser Interface
##//////////////////////////////////////////////////////

from nltk.parse import ParserI

class ChunkParserI(ParserI):
    """
    A processing interface for identifying non-overlapping groups in
    unrestricted text.  Typically, chunk parsers are used to find base
    syntactic constituants, such as base noun phrases.  Unlike
    L{ParserI}, C{ChunkParserI} guarantees that the C{parse} method
    will always generate a parse.
    """
    def parse(self, tokens):
        """
        Find the best chunk structure for the given tokens
        and return a tree.
        
        @param tokens: The list of (word, tag) tokens to be chunked.
        @type tokens: L{list} of L{tuple}
        """
        assert 0, "ChunkParserI is an abstract interface"
