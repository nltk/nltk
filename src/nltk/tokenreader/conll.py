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

    def read_token(self, s, add_contexts=False, add_locs=False, source=None):
        """
        @return: A token containing the chunked tagged text that is
            encoded in the given CONLL 2000 style string.
        @rtype: L{Token}
        @param add_contexts: If true, then add a subtoken context
            pointer to each subtoken.
        @param add_locs: If true, then add locations to each subtoken.
            Locations are based on sentence and word index numbers.
        @param source: The soruce for subtokens' locations (ignored
            unless C{add_locs=True}
        """
        sentences = re.split('\s*\n\s*\n\s*', s)
        if sentences[0] == '': sentences = sentences[1:]
        if sentences[-1] == '': sentences = sentences[:-1]

        sent_toks = [self._read_sent(sent, source)
                     for sent in sentences]

        result = Token(SENTS=sent_toks)

        # Add locations, if requested.
        if add_locs:
            for sent_num, sent_tok in enumerate(sent_toks):
                sent_loc = SentIndexLocation(sent_num, source)
                sent_tok['LOC'] = sent_loc
                for word_num, word_tok in enumerate(sent_tok['WORDS']):
                    word_loc = WordIndexLocation(word_num, sent_loc)
                    word_tok['LOC'] = word_loc

        # Add contexts, if requested.
        if add_contexts:
            for sent_num, sent_tok in enumerate(sent_toks):
                context = SubtokenContextPointer(result, 'SENTS', sent_num)
                sent_tok['CONTEXT'] = context
                for word_num, word_tok in enumerate(sent_tok['WORDS']):
                    context = SubtokenContextPointer(result,'WORDS',word_num)
                    word_tok['CONTEXT'] = context

        return result

    def read_tokens(self, s, add_contexts=False, add_locs=False, source=None):
        """
        @return: A list containing a single token, containing the
            chunked tagged text that is encoded in the given CONLL
            2000 style string.
        @rtype: L{Token}
        @param add_contexts: If true, then add a subtoken context
            pointer to each subtoken.
        @param add_locs: If true, then add locations to each subtoken.
            Locations are based on sentence and word index numbers.
        @param source: The soruce for subtokens' locations (ignored
            unless C{add_locs=True}
        """
        return [self.read_token(s, add_contexts, add_locs, source)]
    
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
