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
from nltk.tree import *
from nltk.tokenreader import TokenReaderI
from nltk import PropertyIndirectionMixIn
import re

class ConllTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader that splits a string of chunked tagged text in the
    CONLL 2000 chunking format into tokens and chunks.  
    The input string is in the form of one tagged token per line.
    Chunks are of three types, NP, VP and PP.  Each type is tagged
    with B(egin), I(nside), or O(utside), to indicate whether we are
    at the beginning of a new chunk, inside an existing chunk, or
    outside a chunk.  Sentences are separated by blank lines.
    """
    def __init__(self, chunk_types=None, **property_names):
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._chunk_types = chunk_types

    def read_token(self, s, source=None):

        sentences = re.split('\s*\n\s*\n\s*', s)
        if sentences[0] == '': sentences = sentences[1:]
        if sentences[-1] == '': sentences = sentences[:-1]

        sent_toks = [self._read_sent(sent, source)
                     for sent in sentences]

        return Token(SENTS=sent_toks)

    def read_tokens(self, s, source=None):
        return [self.read_token(s, source)]
    
    _LINE_RE = re.compile('(\S+)\s+(\S+)\s+([BIO])-?(\S+)?')
    def _read_sent(self, s, source):
        stack = [Tree('S', [])]
        
        for lineno, line in enumerate(s.split('\n')):
            # Decode the line.
            match = self._LINE_RE.match(line)
            if match is None:
                raise ValueError, 'Error on line %d' % lineno
            (word, tag, state, chunk_type) = match.groups()
            
            # If it's a chunk type we don't care about, treat it as O.
            if (self._chunk_types is not None and
                chunk_type not in self._chunk_types):
                state = 'O'

            # For "Begin"/"Outside", finish any completed chunks.
            if state in 'BO':
                if len(stack) == 2: stack.pop()

            # For "Begin", start a new chunk.
            if state == 'B':
                chunk = Tree(chunk_type, [])
                stack[-1].append(chunk)
                stack.append(chunk)

            # For "Inside", perform a sanity check.
            if state == 'I':
                if len(stack) != 2 or chunk_type != stack[-1].node:
                    raise ValueError, 'Error on line %d' % lineno
                
            # Add the new word token.
            word = Token(TEXT=word, TAG=tag)
            stack[-1].append(word)

        # Create and return the sentence token
        tree = stack[-1]
        return Token(TREE=tree, WORDS=tree.leaves())
