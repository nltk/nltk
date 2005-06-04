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

class TreebankTokenReader3LB(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader that reads 3LB treebank-style trees.  By default,
    tokens are created that contain two properties: C{TREE} and
    C{SUBTOKENS}.  The subtokens are shared as tree leaves and
    elements of the subtoken list.  Each subtoken defines the C{TEXT}
    property.  Optional arguments can be used to add the C{LOC} and
    C{CONTEXT} properties to each subtoken.
    It returns a list of trees from a file.

    @outprop: C{TREE}: The token's tree structure.
    @outprop: C{SUBTOKENS}: A list of the tree's leaves.
    @outprop: C{TEXT}: The text of the tree's subtokens.
    @outprop: C{TAG}: The tag of the tree's subtokens.  This is
        only used if the C{preterminal_tags} parameter to the
        constructor is set to C{True}.
    """
    def __init__(self, preterminal_tags=False, **property_names):
        """
        @param preterminal_tags: If true, then treat preterminal
            nodes as tags.
        @type preterminal_tags: C{boolean}
        """
        self.conversion = re.compile(r"(?P<espacio> )"r"(?P<lemma>[^ ]+?)"r"(?P<parentheses>\)+?)",re.DOTALL)
        #self.ceros = re.compile(r"(?P<espacio> )"r"(?P<ceros>\*0\*)"r"(?P<parentheses>\)+?)",re.DOTALL)
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._preterminal_tags = preterminal_tags
        self._source = None # <- not thread-safe.

    def read_token(self, s, add_contexts=False, add_subtoks=True,
                   add_locs=False, add_lemmas=True,source=None):
        """
        @return: A token containing the treebank tree encoded by
            the string C{s}.
        @rtype: L{Token}
        @type add_locs: C{bool}
        @param add_locs: Should this token reader add the C{LOC}
            property to each subtoken?  If true, then this property
            will map to a L{CharSpanLocation} object, whose character
            indices are defined over the input string.
        @param add_lemmas: Should this token reader add the
            C{LEMMA} property to each subtoken?  If true, then this
            property will map to a L{LEMMA} object for
            the subtoken.
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
        treetoks = self.read_tokens(s, add_contexts, add_subtoks,
                                    add_locs, source)
        if len(treetoks) == 0:
            raise ValueError, 'No tree found'
        elif len(treetoks) > 1:
            raise ValueError, 'Multiple trees found'
        else:
            return treetoks[0]

    def read_tokens(self, s, add_contexts=False, add_subtoks=True,
                   add_locs=False, add_lemmas=True, source=None):
        """
        @return: A list of tokens containing the treebank trees
            encoded by the string C{s}.
        @rtype: L{Token}
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
        @param add_lemmas: Should this token reader add the
            C{LEMMA} property to each subtoken?  If true, then this
            property will map to a L{LEMMA} object for
            the subtoken.
        @type add_subtoks: C{bool}
        @param add_subtoks: Should this token reader add the C{SUBTOKENS}
            property to the returned token?  If true, the C{SUBTOKENS}
            will contain a list of the trees leaves.
        """
        TREE = self.property('TREE')
        SUBTOKENS = self.property('SUBTOKENS')
        self._source = source
        s = re.sub(r" \*0\*\)",r" \*-0-\* null)",s)
        s = re.sub(self.conversion,"@@=@@"+"\g<lemma>"+"\g<parentheses>",s)
        if add_lemmas:
            #print "add_lemmas"
            if add_locs:
                leafparser = self._locs_leafparser
            else:
                leafparser = self._nolocs_leafparser
        else:
            #print "NO ADD_LEMMAS"
            if add_locs:
                leafparser = self._locs_leafparser_nolemma
            else:
                leafparser = self._nolocs_leafparser_nolemma
        
        treetoks = []
        for tree in Tree.parse_iter(s, leafparser=leafparser):
            # If the tree has an extra level with node='', then get
            # rid of it.  (E.g., "((S (NP ...) (VP ...)))")
            if len(tree) == 1 and tree.node == '':
                tree = tree[0]
            
            # Create a token, and add it to the list.
            treetok = Token(**{TREE: tree})
            treetoks.append(treetok)
            
            # Add contexts to leaf tokens, if requested.
            if add_contexts:
                self._add_contexts_to_leaves(treetok, tree, ())

            # Add the SUBTOKENS property, if requested
            if add_subtoks:
                treetoks[-1][SUBTOKENS] = tree.leaves()

            # Convert preterminals into tags, if requested.
            if self._preterminal_tags:
                self._convert_preterminals_to_tags(tree)

        # Return the list
        return treetoks

    def _convert_preterminals_to_tags(self, tree):
        TAG = self.property('TAG')
        for i, child in enumerate(tree):
            #print "i: ",i
            #print "child: ",child
            if isinstance(child, Tree):
                #print " If it's a preterminal, convert it."
                if len(child) == 1 and isinstance(child[0], Token):
                    child[0][TAG] = child.node
                    #print "tree[i],child[0] -> ",tree[i],child[0]
                    tree[i] = child[0]
                
                else:
                    #print " Otherwise, recurse."
                    self._convert_preterminals_to_tags(child)

    def _locs_leafparser(self, text, (start, end)):
        TEXT = self.property('TEXT')
        LEMMA = self.property('LEMMA')
        LOC = self.property('LOC')
        t,l = text.split("@@=@@")
        tok = Token(**{TEXT: t})
        tok["LEMMA"] = l
        tok[LOC] = CharSpanLocation(start, end, self._source)
        return tok

    def _nolocs_leafparser(self, text, (start, end)):
        TEXT = self.property('TEXT')
        LEMMA = self.property('LEMMA')
        LOC = self.property('LOC')
        #print "In _nolocs_leafparser, text - >",text
        t,l = text.split("@@=@@")
        tok = Token(**{TEXT: t})
        tok["LEMMA"] = l
        #print "  and tok is: ",tok
        return tok

    def _locs_leafparser_nolemma(self, text, (start, end)):
        #print text
        TEXT = self.property('TEXT')
        #LEMMA = self.property('LEMMA')
        LOC = self.property('LOC')
        t,l = text.split("@@=@@")
        tok = Token(**{TEXT: t})
        #tok["LEMMA"] = l
        tok[LOC] = CharSpanLocation(start, end, self._source)
        return tok

    def _nolocs_leafparser_nolemma(self, text, (start, end)):
        #print text
        TEXT = self.property('TEXT')
        #LEMMA = self.property('LEMMA')
        LOC = self.property('LOC')
        #print "In _nolocs_leafparser, text - >",text
        t,l = text.split("@@=@@")
        tok = Token(**{TEXT: t})
        #tok["LEMMA"] = l
        #print "  and tok is: ",tok
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
    def __init__(self, preterminal_tags=False,  **property_names):
        self._tb_reader = TreebankTokenReader(preterminal_tags,
                                              **property_names)

    def property(self, name):
        return self._tb_reader.property(name)

    def read_token(self, s, add_contexts=False, add_subtoks=True,
                   add_locs=False, source=None):
        treetoks = self._tb_reader.read_tokens(s, add_contexts, add_subtoks,
                                               add_locs, source)
        return Token(**{self.property('SENTS'): treetoks})

    def read_tokens(self, s, add_contexts=False, add_subtoks=True,
                   add_locs=False, source=None):
        return [self.read_token(s, add_contexts, add_subtoks,
                                add_locs, source)]
    
