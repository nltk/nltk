# Natural Language Toolkit: A Chunk Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

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

Helper Functions
================

The C{nltk.chunkparser} module also defines two helper classes and
functions:

    - C{ChunkedTaggedTokenizer} is a tagged tokenizer that is
      sensitive to chunks that are delimited by brackets ([]).  It
      converts a string to a chunk structure.
    - C{ChunkScore} is a utility class for scoring chunk parsers.  It
      can evaluate chunk parsing based on a number of statistics
      (precision, recall, f-measure, misssed chunks, incorrect
      chunks).  It can also combine the scores from the parsing of
      multiple texts; this makes it signifigantly easier to evaluate a
      chunk parser that operates one sentence at a time.
    - C{unchunk} converts a chunk structure to a list of tagged
      tokens, by removing all chunking.
"""

from nltk.token import TokenizerI, Token, Location
from nltk.chktype import chktype as _chktype
from nltk.set import Set
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

def unchunk(chunked_sent):
    """
    Convert a chunk structure to a list of tokens, by removing all
    chunking.  This function removes the nested-list structure of a
    chunk structure, and returns the flat list of tokens contained in
    C{chunked_sent}.

    @param chunked_sent: The chunk structure to be unchunked.
    @type chunked_sent: C{list} of (C{TaggedToken} or (C{list} of C{TaggedToken}))
    @return: The flat list of tokens contained in C{chunked_sent}.
    @rtype: C{list} of C{TaggedToken}
    """
    unchunked_sent = []
    for token in chunked_sent:
        if isinstance(token, Token):
            unchunked_sent.append(token)
        else:
            unchunked_sent.extend(token)
    return unchunked_sent

class ChunkScore:
    """
    A utility class for scoring chunk parsers.  C{ChunkScore} can
    evaluate a chunk parser's output, based on a number of statistics
    (precision, recall, f-measure, misssed chunks, incorrect chunks).
    It can also combine the scores from the parsing of multiple texts;
    this makes it signifigantly easier to evaluate a chunk parser that
    operates one sentence at a time.

    Texts are evaluated with the C{score} method.  The results of
    evaluation can be accessed via a number of accessor methods, such
    as C{precision} and C{f_measure}.  A typical use of the
    C{ChunkScore} class is::

        >>> chunkscore = ChunkScore()
        >>> for correct in correct_sentences:
        ...     guess = chunkparser.parse(unchunk(correct))
        ...     chunkscore.score(correct, guess)
        >>> chunkscore.score(correct2, guessed2)
        >>> print 'F Measure:', chunkscore.f_measure()
        F Measure: 0.823

    @type _correct: C{Set} of chunk token.
    @ivar _correct: The known-correct (gold standard) chunks
    @type _guessed: C{Set} of chunk token.
    @ivar _guessed: The guessed chunks
    """
    def __init__(self):
        self._correct = Set()
        self._guessed = Set()
        self._len = 0

    def score(self, correct, guessed):
        """
        Given a correctly chunked text, score another chunked text.
        Merge the results with all previous scorings.  Note that when
        the score() function is used repeatedly, each token I{must}
        have a unique location.  For sentence-at-a-time chunking, it
        is recommended that you use locations like C{@12w@3s} (the
        word at index 12 of the sentence at index 3).
        
        @type correct: chunk structure
        @param correct: The known-correct ("gold standard") chunked
            sentence.
        @type guessed: chunk structure
        @param guessed: The chunked sentence to be scored.
        """
        self._correct = self._correct.union(self._chunk_locs(correct))
        self._guessed = self._guessed.union(self._chunk_locs(guessed))
        self._len += len(unchunk(correct))

    def precision(self):
        """
        @return: the overall precision for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        return self._correct.precision(self._guessed)
    
    def recall(self):
        """
        @return: the overall recall for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        return self._correct.recall(self._guessed)
    
    def f_measure(self, alpha=0.5):
        """
        @return: the overall F measure for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        
        @param alpha: the relative weighting of precision and recall.
            Larger alpha biases the score towards the precision value,
            while smaller alpha biases the score towards the recall
            value.  C{alpha} should have a value in the range [0,1].
        @type alpha: C{float}
        """
        return self._correct.f_measure(self._guessed, alpha)
    
    def missed(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the
            correct chunk structures, but not in the guessed chunk
            structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the missed chunks.
        """
        return self._correct - self._guessed
    
    def incorrect(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the
            guessed chunk structures, but not in the correct chunk
            structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the incorrect chunks.
        """
        return self._guessed - self._correct
    
    def correct(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the correct
            chunk structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the correct chunks.
        """
        return self._correct

    def guessed(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the guessed
            chunk structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the guessed chunks.
        """
        return self._guessed
    
    def __repr__(self):
        """
        @rtype: C{String}
        @return: a concise representation of this C{ChunkScoring}.
        """
        return '<ChunkScoring of '+`self._len`+' tokens>'

    def __str__(self):
        """
        @rtype: C{String}
        @return: a verbose representation of this C{ChunkScoring}.
            This representation includes the precision, recall, and
            f-measure scores.  For other information about the score,
            use the accessor methods (e.g., C{missed()} and
            C{incorrect()}). 
        """
        return ("ChunkParser score:\n" +
                ("    Precision: %5.1f%%\n" % (self.precision()*100)) +
                ("    Recall:    %5.1f%%\n" % (self.recall()*100))+
                ("    F-Measure: %5.1f%%\n" % (self.f_measure()*100)))
        
    def _seq_loc(self, tok_sent):
        """
        Return the location spanning a tokenized sentence
        """
        loc0 = tok_sent[0].loc()
        locn = tok_sent[-1].loc()
        return Location(loc0.start(), locn.end(),
                        unit=loc0.unit(), source=loc0.source()) 

    def _unify(self, tok_sent):
        """
        Construct a unified "chunk token" containing the merged
        contents of a chunk.  This makes it much easier to tell what
        chunks were missed or were generated incorrectly.
        """
        words = [tok.type().base() for tok in tok_sent]
        str = ' '.join(words)
        return Token(str, self._seq_loc(tok_sent))

    # get the locations of chunks in a chunked sentence
    def _chunk_locs(self, chunked_sent):
        locs = []
        for piece in chunked_sent:
            if type(piece) == type([]):
                locs.append(self._unify(piece))
                #locs.append(_seq_loc(piece))
        return Set(*locs)
