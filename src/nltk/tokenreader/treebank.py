# Natural Language Toolkit: Treeabank Token Readers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

import re
from nltk.token import *
from nltk.tokenreader import TokenReaderI
from nltk import PropertyIndirectionMixIn
from nltk.chktype import chktype
from nltk.tokenreader.tagged import ChunkedTaggedTokenReader
from nltk.tree import Tree

"""
Token readers for reading tokens encoded with treebank-style strings.
"""

#################################################################
# Treebank Token Readers
#################################################################

class TreebankTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader that reads treebank-style trees.  By default,
    tokens are created that contain two properties: C{TREE} and
    C{SUBTOKENS}.  The subtokens are shared as tree leaves and
    elements of the subtoken list.  Each subtoken defines the C{TEXT}
    property.  Optional arguments can be used to add the C{LOC} and
    C{CONTEXT} properties to each subtoken.

    @outprop: C{TREE}: The token's tree structure.
    @outprop: C{SUBTOKENS}: A list of the tree's leaves.
    @outprop: C{TEXT}: The text of the tree's subtokens.
    """
    def __init__(self, add_locs=False, add_contexts=False, 
                 add_subtoks=True, **property_names):
        """
        @type add_locs: C{bool}
        @param add_locs: Should this token reader add the C{LOC}
            property to each subtoken?  If true, then this property
            will map to a L{CharSpanLocation} object, whose character
            indices are defined over the input string.
        @type add_contexts: C{bool}
        @param add_contexts: Should this token reader add the
            C{CONTEXT} property to each subtoken?  If true, then this
            property will map to a L{TreeContextPointer} object for
            the subtoken.
        @type add_subtoks: C{bool}
        @param add_subtoks: Should this token reader add the C{SUBTOKENS}
            property to the returned token?  If true, the C{SUBTOKENS}
            will contain a list of the trees leaves.
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._add_locs = add_locs
        self._add_contexts = add_contexts
        self._add_subtoks = add_subtoks
        self._source = None # <- not thread-safe.

    def read_token(self, s, source=None):
        treetoks = self.read_tokens(s, source)
        if len(treetoks) == 0:
            raise ValueError, 'No tree found'
        elif len(treetoks) > 1:
            raise ValueError, 'Multiple trees found'
        else:
            return treetoks[0]

    def read_tokens(self, s, source=None):
        TREE = self.property('TREE')
        SUBTOKENS = self.property('SUBTOKENS')
        self._source = source
        
        treetoks = []
        for tree in Tree.parse_iter(s, leafparser=self._leafparser):
            # If the tree has an extra level with node='', then get
            # rid of it.  (E.g., "((S (NP ...) (VP ...)))")
            if len(tree) == 1 and tree.node == '':
                tree = tree[0]
            
            # Create a token, and add it to the list.
            treetok = Token(**{TREE: tree})
            treetoks.append(treetok)
            
            # Add contexts to leaf tokens, if requested.
            if self._add_contexts:
                self._add_contexts_to_leaves(treetok, tree, ())

            # Add the SUBTOKENS property, if requested
            if self._add_subtoks:
                treetoks[-1][SUBTOKENS] = tree.leaves()

        # Return the list
        return treetoks

    def _leafparser(self, text, (start, end)):
        TEXT = self.property('TEXT')
        LOC = self.property('LOC')
        tok = Token(**{TEXT: text})
        if self._add_locs:
            tok[LOC] = CharSpanLocation(start, end, self._source)
        return tok

    def _add_contexts_to_leaves(self, container, val, path):
        if isinstance(val, Tree):
            for i, child in enumerate(val):
                self._add_contexts_to_leaves(container, child, path+(i,))
        elif isinstance(val, Token):
            CONTEXT = self.property('CONTEXT')
            TREE = self.property('TREE')
            val[CONTEXT] = TreeContextPointer(container, TREE, path)
        else:
            assert 0, 'Unexpected object type in tree'

class TreebankFileTokenReader(TokenReaderI):
    def __init__(self, add_locs=False, add_contexts=False, 
                 add_subtoks=True, **property_names):
        self._tb_reader = TreebankTokenReader(
            add_locs=add_locs, add_contexts=add_contexts,
            add_subtoks=add_subtoks, **property_names)

    def property(self, name):
        return self._tb_reader.property(name)

    def read_token(self, s, source=None):
        treetoks = self._tb_reader.read_tokens(s, source)
        return Token(**{self.property('SUBTOKENS'): treetoks})

    def read_tokens(self, s, source=None):
        return [self.read_token(s, source)]
    
class TreebankTaggedTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader that reas the treebank tagged-file format into a
    token.  In this format:

      - Paragraphs are separated by lines of C{'='} characters.
      - Sentences are separated by words tagged as sentence-final
        punctuation (e.g., C{'./.'}).
      - NP chunk structure is encoded with square brackets (C{[...]}).
      - Words are separated by whitespace or square brackets.
      - Each word has the form C{I{text}/i{tag}}, where C{I{text}}
        is the word's text, and C{I{tag}} is its tag.

    In the returned token:
    
      - The returned token describes a single document.
      - The document's C{PARAS} property contains a list of paragraph
        tokens.
        - Each paragraph token's C{SENTS} property contains a list of
          sentence tokens.
          - Each sentence token's C{WORDS} property contains a list of
            word tokens.
            - Each word token's C{TEXT} property contains the word's
              text.
            - Each word token's C{TAG} property contains the word's
              tag.
            - Depending on the arguments to the reader's constructor,
              each word token may also define the C{LOC} and
              C{CONTEXT} properties.
          - Each sentence token's C{TREE} property contains the
            chunk structures in the text.  In the case of the Treebank,
            these chunk structures were generated by a stochastic NP
            chunker as part of the PARTS preprocessor, and \"are best
            ignored.\"
    """
    def __init__(self, add_locs=False, add_contexts=False,
                 **property_names):
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._add_locs = add_locs
        self._add_contexts = add_contexts

        # A token reader for processing sentences.
        self._sent_reader = ChunkedTaggedTokenReader(
            add_locs, add_contexts, top_node='S', chunk_node='NP_CHUNK',
            **property_names)

    def read_token(self, s, source=None):
        assert chktype(1, s, str)

        TEXT = self.property('TEXT')
        LOC = self.property('LOC')
        CONTEXT = self.property('CONTEXT')
        SENTS = self.property('SENTS')
        PARAS = self.property('PARAS')
        TREE = self.property('TREE')

        # Split into paragraphs.
        paragraphs = re.split(r'(?m)^={10,}$', s)
        # Strip whitespace, and discard empty paras.
        paragraphs = [para.strip() for para in paragraphs]
        paragraphs = [para for para in paragraphs if para]

        # Process each paragraph.
        para_toks = []
        for para_num, para_text in enumerate(paragraphs):
            # Create a location for this paragraph
            para_loc = ParaIndexLocation(para_num, source)
            # Split the paragraph into sentences.
            sentences = re.findall('(?s)\S.*?/\.', para_text)
            sent_toks = []
            for sent_num, sentence in enumerate(sentences):
                sent_loc = SentIndexLocation(sent_num, para_loc)
                sent_tok = self._sent_reader.read_token(sentence, sent_loc)
                sent_toks.append(sent_tok)
            para_toks.append(Token(**{SENTS: sent_toks}))
            if self._add_locs:
                para_toks[-1][LOC] = para_loc

        # Create a token for the document
        tok = Token(**{PARAS: para_toks})

        # Add context pointers, if requested
        if self._add_contexts:
            for para_num, para_tok in enumerate(tok[PARAS]):
                para_tok[CONTEXT] = SubtokenContextPointer(tok, PARAS,
                                                           para_num)
                for sent_num, sent_tok in enumerate(para_tok[SENTS]):
                    sent_tok[CONTEXT] = SubtokenContextPointer(tok, SENTS,
                                                               sent_num)

        # Return the finished token.
        return tok
            
    def read_tokens(self, s, source=None):
        return [self.read_token(s, source)]
    
