# Natural Language Toolkit: IEER Token Reader
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Token reader for the reading tokens encoded with IEER-style strings.
"""

from nltk.token import *
from nltk.tokenreader import TokenReaderI
from nltk import PropertyIndirectionMixIn
import re

class IeerTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader that splits a string of chunked tagged text in the
    IEER named entity format into tokens and chunks.  The input string
    is in the form of a document (the IEER corpus reader returns a
    list of such documents).  Chunks are of several types, LOCATION,
    ORGANIZATION, PERSON, DURATION, DATE, CARDINAL, PERCENT, MONEY,
    and MEASURE.  Each token returned corresponds to a single
    document, and defines the following properties:

      - C{TREE}: The chunked tree for the document's text.  Children
        are either word tokens or chunks.
      - C{WORDS}: A list of the words in the document's text.  This is
        equal to the leaves of C{TREE}.
      - C{DOCNO}: The document number identifier for the document.
      - C{DOCTYPE}: The document type.
      - C{DATETIME}: The time and date of the document.
      - C{HEADLINE}: A tokenized list of the words in the document.
    """

    def __init__(self, chunk_types = ['LOCATION', 'ORGANIZATION', 'PERSON', 
            'DURATION', 'DATE', 'CARDINAL', 'PERCENT', 'MONEY', 'MEASURE'],
                 **property_names):
        """
        Create a new C{IeerChunkedTokenizer}.
        
        @type chunk_types: C{string}
        @param chunk_types: A list of the node types to be extracted
            from the input.  Possible node types are
            C{'LOCATION'}, C{'ORGANIZATION'}, C{'PERSON'},
            C{'DURATION'}, C{'DATE'}, C{'CARDINAL'}, C{'PERCENT'},
            C{'MONEY'}, C{'MEASURE'}
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._chunk_types = chunk_types

    _DOC_RE = re.compile(r'<DOC>\s*'
                         r'(<DOCNO>\s*(?P<docno>.+?)\s*</DOCNO>\s*)?'
                         r'(<DOCTYPE>\s*(?P<doctype>.+?)\s*</DOCTYPE>\s*)?'
                         r'(<DATE_TIME>\s*(?P<date_time>.+?)\s*</DATE_TIME>\s*)?'
                         r'<BODY>\s*'
                         r'(<HEADLINE>\s*(?P<headline>.+?)\s*</HEADLINE>\s*)?'
                         r'<TEXT>(?P<text>.*?)</TEXT>\s*'
                         r'</BODY>\s*</DOC>\s*', re.DOTALL)

    _TYPE_RE = re.compile('<b_\w+\s+[^>]*?type="(?P<type>\w+)"')

    def read_token(self, s, add_contexts=False, add_locs=False, source=None):
        """
        @return: A token containing the chunked tagged text that is
            encoded in the given IEER style string.
        @rtype: L{Token}
        @param add_contexts: If true, then add a subtoken context
            pointer to each subtoken.
        @param add_locs: If true, then add locations to each subtoken.
            Locations are based on sentence and word index numbers.
        @param source: The soruce for subtokens' locations (ignored
            unless C{add_locs=True}
        """
        TREE = self.property('TREE')
        
        # Try looking for a single document.  If that doesn't work, then just
        # treat everything as within the <TEXT>...</TEXT>.
        m = self._DOC_RE.match(s)
        if m:
            tok = self._read_doc_match(m)
        else:
            tok = Token(**{TREE: self._read_text(s)})

        # Add WORDS, LOC, CONTEXT
        self._add_derived_props(tok)

        return tok

    def read_tokens(self, s, add_contexts=False, add_locs=False, source=None):
        """
        @return: A list containing a single token, containing the
            chunked tagged text that is encoded in the given IEER
            style string.
        @rtype: L{Token}
        @param add_contexts: If true, then add a subtoken context
            pointer to each subtoken.
        @param add_locs: If true, then add locations to each subtoken.
            Locations are based on sentence and word index numbers.
        @param source: The soruce for subtokens' locations (ignored
            unless C{add_locs=True}
        """
        TREE = self.property('TREE')
        toks = [self._read_doc_match(m) for m in self._DOC_RE.finditer(s)]
        # If we didn't find any docs, try treating it as a single doc,
        # without the enclosing html headers.
        if len(toks) == 0:
            toks = [Token(**{TREE: self._read_text(s)})]

        # Add WORDS, LOC, CONTEXT
        for tok in toks:
            self._add_derived_props(tok)

        return toks

    def _add_derived_props(self, tok, add_contexts, add_locs, source):
        WORDS = self.property('WORDS')
        TREE = self.property('TREE')
        CONTEXT = self.property('CONTEXT')
        LOC = self.property('LOC')
        
        # Add the WORDS property.
        tok[WORDS] = tok[TREE].leaves()

        # Add context pointers, if requested.
        if add_contexts:
            for i, word_tok in enumerate(tok[WORDS]):
                cp = SubtokenContextPointer(tok, WORDS, i)
                word_tok[CONTEXT] = cp

        # Add locations, if requested
        if add_locs:
            for i, word_tok in enumerate(tok[WORDS]):
                word_tok[LOC] = WordIndexLocation(i, source)

    def _read_doc_match(self, m):
        DOCNO = self.property('DOCNO')          # string
        DOCTYPE = self.property('DOCTYPE')      # string
        DATE_TIME = self.property('DATE_TIME')  # string
        HEADLINE = self.property('HEADLINE')    # list of tokens
        TEXT = self.property('TEXT')            # string
        TREE = self.property('TREE')            # tree over tokens

        tok = Token(**{TREE: self._read_text(m.group('text'))})
        tok[DOCNO]=m.group('docno')
        tok[DOCTYPE]=m.group('doctype')
        tok[DATE_TIME]=m.group('date_time')
        tok[HEADLINE]=[Token(**{TEXT: t})
                       for t in m.group('headline').split()]
        return tok

    def _read_text(self, s):
        stack = [Tree('TEXT', [])]
        for piece_m in re.finditer('<[^>]+>|[^\s<]+', s):
            piece = piece_m.group()
            try:
                if piece.startswith('<b_'):
                    m = self._TYPE_RE.match(piece)
                    if m is None: print 'XXXX', piece
                    chunk = Tree(m.group('type'), [])
                    stack[-1].append(chunk)
                    stack.append(chunk)
                elif piece.startswith('<e_'):
                    stack.pop()
                elif piece.startswith('<'):
                    raise ValueError # Unexpected HTML
                else:
                    stack[-1].append(Token(TEXT=piece))
            except (IndexError, ValueError):
                raise ValueError('Bad IEER string (error at character %d)' %
                                 piece_m.start())
        if len(stack) != 1:
            raise ValueError('Bad IEER string')
        return stack[0]

