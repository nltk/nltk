# Natural Language Toolkit: Tagged Token Readers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Token readers for reading tagged tokens encoded with slashed tags.
"""

from nltk.token import *
from nltk.tree import Tree
from nltk.tokenreader import TokenReaderI
from nltk import PropertyIndirectionMixIn
import re

class TaggedTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader that divides a string of tagged words into
    subtokens.  Words should be separated by whitespace, and each word
    should have the form C{I{text}/I{tag}}, where C{I{text}} specifies
    the word's C{TEXT} property, and C{I{tag}} specifies its C{TAG}
    property.  Words that do not contain a slash are assigned a C{tag}
    of C{None}.
    
    @outprop: C{SUBTOKENS}: The list of subtokens.
    @outprop: C{TEXT}: The subtokens' text contents.
    @outprop: C{TAG}: The subtokens' tags.
    """
    def __init__(self, **property_names):
        PropertyIndirectionMixIn.__init__(self, **property_names)

    # [XX] sourceis ignored!
    def read_token(self, s, source=None):
        TAG = self.property('TAG')
        TEXT = self.property('TEXT')
        SUBTOKENS = self.property('SUBTOKENS')
        subtoks = []
        for w in s.split():
            slash = w.find('/')
            if slash >= 0:
                subtoks.append(Token(**{TEXT: w[:slash], TAG: w[slash+1:]}))
            else:
                subtoks.append(Token(**{TEXT: w, TAG: None}))
        return Token(**{SUBTOKENS: subtoks})

    def read_tokens(self, s, source=None):
        return [self.read_token(s, source)]


class ChunkedTaggedTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader that divides a string of chunked tagged text into
    chunks and unchunked tokens.  Each chunk is encoded as a C{Tree}
    whose children are tagged word tokens.  Each unchunked token is
    encoded as a tagged word token.

    Chunks are marked by square brackets (C{[...]}).  Words are
    deliniated by whitespace, and each word should have the form
    C{I{text}/I{tag}}, where C{I{text}} specifies the word's C{TEXT}
    property, and C{I{tag}} specifies the word's C{TAG} property.
    Words that do not contain a slash are assigned a C{tag} of
    C{None}.

      >>> ctt = ChunkedTaggedTokenizer('NP', SUBTOKENS='WORDS')
      >>> tok = Token(TEXT='[The/DT dog/NN] saw/VBD [him/PRP]')
      >>> ctt.tokenize(tok)
      >>> print tok['WORDS']
      [(NP: <The/DT> <dog/NN>), <saw/VBD>, (NP: <him/PRP>)]
    
    The C{Tree} constructor can be used to group this list of
    tokens and chunks into a single chunk structure:

      >>> chunkstruct = Tree('S', tok['WORDS'])
      (S: (NP: <The/DT> <dog/NN>) <saw/VBD> (NP: <him/PRP>))
        
    @inprop: C{TEXT}: The input token's text content.
    @inprop: C{LOC}: The input token's location.  I{(optional)}
    @outprop: C{SUBTOKENS}: The list of tokenized subtokens.
    @outprop: C{TEXT}: The subtokens' text contents.
    @outprop: C{TAG}: The subtokens' tags.
    @outprop: C{LOC}: The subtokens' locations.
    """
    def __init__(self, locs=False, contexts=False,
                 top_node='S', chunk_node='CHUNK', **property_names):
        """
        @include: AbstractTokenizer.__init__
        @type chunk_node: C{string}
        @param chunk_node: The node label that should be used for
            chunk subtrees.  This is typically a short string
            describing the type of information contained by the chunk,
            such as C{"NP"} for base noun phrases.
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._locs = locs
        self._contexts = contexts
        self._chunk_node = chunk_node
        self._top_node = top_node

    _WORD_OR_BRACKET = re.compile(r'\[|\]|[^\[\]\s]+')
    _VALID = re.compile(r'^([^\[\]]+|\[[^\[\]]*\])*$')
    
    def read_token(self, s, source=None):
        TEXT = self.property('TEXT')
        TAG = self.property('TAG')
        SUBTOKENS = self.property('SUBTOKENS')
        LOC = self.property('LOC')
        TREE = self.property('TREE')
        CONTEXT = self.property('CONTEXT')
        
        # Check that it's valid here, so we don't have to keep
        # checking later.
        if not self._VALID.match(s):
            raise ValueError, 'Invalid token string (bad brackets)'
        
        stack = [Tree(self._top_node, [])]
        for match in self._WORD_OR_BRACKET.finditer(s):
            text = match.group()
            if text[0] == '[':
                chunk = Tree(self._chunk_node, [])
                stack[-1].append(chunk)
                stack.append(chunk)
            elif text[0] == ']':
                stack.pop()
            else:
                slash = text.find('/')
                if slash >= 0:
                    tok = Token(**{TEXT: text[:slash], TAG: text[slash+1:]})
                else:
                    tok = Token(**{TEXT: text, TAG: None})
                if self._locs:
                    start, end = match.span()
                    if slash >= 0: end = start+slash
                    tok[LOC] = CharSpanLocation(start, end, source)
                stack[-1].append(tok)

        # Create the token, and add the TREE property.
        tok = Token(**{TREE: stack[0]})
        # Add the SUBTOKENS property (from the tree's leaves)
        tok[SUBTOKENS] = leaves = tok[TREE].leaves()
        # Add context pointers.
        if self._contexts:
            for i, subtok in enumerate(leaves):
                subtok[CONTEXT] = SubtokenContextPointer(tok, SUBTOKENS, i)
        return tok

    def read_tokens(self, s, source=None):
        return [self.read_token(s, source)]

