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

"""
Re-impl of chunkscore..
  1. keep running counts of: tp, fp, tn
  2. These can be used to generate most statistics
  3. keep list of tp, fp, tn??  tp+fn = correct; tp+fp = guessed
"""

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

    @ivar kwargs: Keyword arguments:

        - max_tp_examples: The maximum number actual examples of true
          positives to record.  This affects the C{correct} member
          function: C{correct} will not return more than this number
          of true positive examples.  This does *not* affect any of
          the numerical metrics (precision, recall, or f-measure)

        - max_fp_examples: The maximum number actual examples of false
          positives to record.  This affects the C{incorrect} member
          function and the C{guessed} member function: C{incorrect}
          will not return more than this number of examples, and
          C{guessed} will not return more than this number of true
          positive examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)
        
        - max_fn_examples: The maximum number actual examples of false
          negatives to record.  This affects the C{missed} member
          function and the C{correct} member function: C{missed}
          will not return more than this number of examples, and
          C{correct} will not return more than this number of true
          negative examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)
        
    @type _tp: C{list} of C{Token}
    @ivar _tp: List of true positives
    @type _fp: C{list} of C{Token}
    @ivar _fp: List of false positives
    @type _fn: C{list} of C{Token}
    @ivar _fn: List of false negatives
    
    @type _tplen: C{int}
    @ivar _tplen: Number of true positives
    @type _fplen: C{int}
    @ivar _fplen: Number of false positives
    @type _fnlen: C{int}
    @ivar _fnlen: Number of false negatives.
    """
    def __init__(self, **kwargs):
        self._tp = []
        self._tplen = 0
        self._fp = []
        self._fplen = 0
        self._fn = []
        self._fnlen = 0
        self._max_tp = kwargs.get('max_tp_examples', 100)
        self._max_fp = kwargs.get('max_fp_examples', 100)
        self._max_fn = kwargs.get('max_fn_examples', 100)

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
        correct = self._chunk_toks(correct)
        guessed = self._chunk_toks(guessed)
        while correct and guessed:
            if correct[-1].loc() == guessed[-1].loc():
                self._tplen += 1
                if len(self._tp) < self._max_tp:
                    self._tp.append(correct[-1])
                correct.pop()
                guessed.pop()
            elif correct[-1].loc().start() >= guessed[-1].loc().end():
                self._fnlen += 1
                if len(self._fn) < self._max_fn:
                    self._fn.append(correct[-1])
                correct.pop()
            else:
                # If a guess is not equal to a correct chunk, but
                # overlaps it in any way, then it must be wrong.
                self._fplen += 1
                if len(self._fp) < self._max_fp:
                    self._fp.append(guessed[-1])
                guessed.pop()

    def precision(self):
        """
        @return: the overall precision for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        div = self._tplen + self._fplen
        if div == 0: return None
        else: return float(self._tplen) / div
    
    def recall(self):
        """
        @return: the overall recall for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        div = self._tplen + self._fnlen
        if div == 0: return None
        else: return float(self._tplen) / div
    
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
        p = self.precision()
        r = self.recall()
        if p is None or r is None:
            return None
        if p == 0 or r == 0:    # what if alpha is 0 or 1?
            return 0
        return 1/(alpha/p + (1-alpha)/r)
    
    def missed(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the
            correct chunk structures, but not in the guessed chunk
            structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the missed chunks.
        """
        return self._fn
    
    def incorrect(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the
            guessed chunk structures, but not in the correct chunk
            structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the incorrect chunks.
        """
        return self._fp
    
    def correct(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the correct
            chunk structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the correct chunks.
        """
        return self._tp + self._fn

    def guessed(self):
        """
        @rtype: C{Set} of C{Token}
        @return: the set of chunks which were included in the guessed
            chunk structures.  Each chunk is encoded as a single token,
            spanning the chunk.  This encoding makes it easier to
            examine the guessed chunks.
        """
        return self._tp + self._fp
    
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
        
    def _chunk_tok(self, chunk):
        """
        Construct a unified "chunk token" containing the merged
        contents of a chunk.  This makes it much easier to tell what
        chunks were missed or were generated incorrectly.
        """
        # Calculate the type
        words = [tok.type().base() for tok in chunk]
        chunktype = ' '.join(words)

        # Calculate the location
        loc0 = chunk[0].loc()
        locn = chunk[-1].loc()
        chunkloc = Location(loc0.start(), locn.end(),
                            unit=loc0.unit(), source=loc0.source())

        # Return the token.
        return Token(chunktype, chunkloc)

    def _chunk_toks(self, chunked_sent):
        toks = []
        for piece in chunked_sent:
            if type(piece) == type([]):
                toks.append(self._chunk_tok(piece))
        return toks
