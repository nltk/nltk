# Natural Language Toolkit: Chunk parsing API
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

##//////////////////////////////////////////////////////
##  Chunk Parser Interface
##//////////////////////////////////////////////////////

from nltk.parse import ParserI

from nltk.chunk.util import ChunkScore

class ChunkParserI(ParserI):
    """
    A processing interface for identifying non-overlapping groups in
    unrestricted text.  Typically, chunk parsers are used to find base
    syntactic constituents, such as base noun phrases.  Unlike
    ``ParserI``, ``ChunkParserI`` guarantees that the ``parse()`` method
    will always generate a parse.
    """
    def parse(self, tokens):
        """
        Return the best chunk structure for the given tokens
        and return a tree.

        :param tokens: The list of (word, tag) tokens to be chunked.
        :type tokens: list(tuple)
        :rtype: Tree
        """
        raise NotImplementedError()

    def evaluate(self, gold):
        """
        Score the accuracy of the chunker against the gold standard.
        Remove the chunking the gold standard text, rechunk it using
        the chunker, and return a ``ChunkScore`` object
        reflecting the performance of this chunk peraser.

        :type gold: list(Tree)
        :param gold: The list of chunked sentences to score the chunker on.
        :rtype: ChunkScore
        """
        chunkscore = ChunkScore()
        for correct in gold:
            chunkscore.score(correct, self.parse(correct.leaves()))
        return chunkscore

