# Natural Language Toolkit: CONLL Token Reader
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Token reader for the reading tokens encoded with CONLL2000-style
strings.  (Under construction)
"""

from nltk.token import *
from nltk.tokenreader import TokenReaderI
from nltk import PropertyIndirectionMixIn

# [XX] THIS IS BROKEN:
#class ConllChunkedTokenizer(TokenizerI):
#    """
#    A tokenizer that splits a string of chunked tagged text in the
#    CONLL 2000 chunking format into tokens and chunks.  Each token is
#    encoded as a C{Token} whose type is C{TaggedType}; and each chunk
#    is encoded as a C{Tree} containing C{Token}s with
#    C{TaggedType} types.
#
#    The input string is in the form of one tagged token per line.
#    Chunks are of three types, NP, VP and PP.  Each type is tagged
#    with B(egin), I(nside), or O(utside), to indicate whether we are
#    at the beginning of a new chunk, inside an existing chunk, or
#    outside a chunk.
#
#      >>> cct = ConllChunkedTokenizer()
#      >>> toks = cct.tokenize('''
#      he PRP B-NP
#      accepted VBD B-VP
#      the DT B-NP
#      position NN I-NP
#      of IN B-PP
#      vice NN B-NP
#      chairman NN I-NP
#      of IN B-PP
#      Carlyle NNP B-NP
#      Group NNP I-NP
#      , , O
#      a DT B-NP
#      merchant NN I-NP
#      banking NN I-NP
#      concern NN I-NP
#      . . O
#      ''')
#      [('NP': 'he'/'PRP')@[0l],
#      ('VP': 'accepted'/'VBD')@[1l],
#      ('NP': 'the'/'DT' 'position'/'NN')@[2l:4l],
#      ('PP': 'of'/'IN')@[4l],
#      ('NP': 'vice'/'NN' 'chairman'/'NN')@[5l:7l],
#      ('PP': 'of'/'IN')@[7l],
#      ('NP': 'Carlyle'/'NNP' 'Group'/'NNP')@[8l:10l],
#      ','/','@[10l],
#      ('NP': 'a'/'DT' 'merchant'/'NN' 'banking'/'NN' 'concern'/'NN')@[11l:15l],
#      '.'/'.'@[15l]]
#
#    The C{Tree} constructor can be used to group this list of
#    tokens and chunks into a single chunk structure:
#
#      >>> chunkstruct = Tree('S', toks)
#      ('S':
#        ('NP': 'he'/'PRP')
#        ('VP': 'accepted'/'VBD')
#        ('NP': 'the'/'DT' 'position'/'NN')
#        ('PP': 'of'/'IN')
#        ('NP': 'vice'/'NN' 'chairman'/'NN')
#        ('PP': 'of'/'IN')
#        ('NP': 'Carlyle'/'NNP' 'Group'/'NNP')
#        ','/','
#        ('NP': 'a'/'DT' 'merchant'/'NN' 'banking'/'NN' 'concern'/'NN')
#        '.'/'.')@[0l:16l]
#
#    Obtain source data for this tokenizer using
#    C{nltk.corpus.chunking.tokenize()}.
#    """
#
#    def __init__(self, chunk_types = ['NP', 'VP', 'PP']):
#        """
#        Create a new C{ConllChunkedTokenizer}.
#        
#        @type chunk_types: C{string}
#        @param chunk_types: A list of the node types to be extracted
#            from the input.  Possible node types are
#            C{"NP"}, C{"VP"}, and C{"PP"}.
#        """
#        self._chunk_types = chunk_types
#        
#    def tokenize(self, str, source=None):
#        # grab lines
#        lines = LineTokenizer().tokenize(str)
#
#        in_chunk = 0        # currently inside a chunk?
#        chunktype = ''      # inside which type (NP, VP, PP)?
#        chunks = []         # accumulated chunks
#        subsequence = []    # accumulated tokens inside next chunk
#
#        for line in lines:
#            (word, tag, chunktag) = line.type().split()
#
#            # if we're ignoring this type of chunk,
#            # flag it as outside (O) the chunks
#            if chunktag[2:4] not in self._chunk_types:
#                chunktag = 'O'
#            token = Token(TaggedType(word, tag), line.loc())
#
#            # finishing the subsequence because we've found something outside
#            # a chunk or because we're beginning a new chunk
#            if in_chunk and chunktag[0] in 'OB':
#                chunks.append(Tree(chunktype, subsequence))
#                subsequence = []
#                in_chunk = 0
#                chunktype = ''
#
#            # beginning (B) or inside (I) subsequence
#            if chunktag[0] in 'IB':
#                chunktype = chunktag[2:4]
#                subsequence.append(token)
#                in_chunk = 1
#
#            # continuing outside subsequence
#            else:
#                chunks.append(token)
#
#        # sentence ended inside a chunk so add those tokens
#        if subsequence:
#            chunks.append(Tree(chunktype, subsequence))
#
#        return chunks

