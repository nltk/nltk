#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Unit tests for TGrep search implementation for NTLK ParentedTrees.

(c) 16 March, 2013 Will Roberts
'''

from builtins import range
from nltk.tree import ParentedTree
from .. import tgrep
import unittest

class TestSequenceFunctions(unittest.TestCase):

    '''
    Class containing unit tests for tgrep.py.
    '''

    def test_tokenize_simple(self):
        '''
        Simple test of tokenization.
        '''
        tokens = tgrep.tgrep_tokenize(u'A .. (B !< C . D) | ![<< (E , F) $ G]')
        self.assertEqual(tokens,
                         [u'A', u'..', u'(', u'B', u'!', u'<', u'C', u'.', u'D', u')',
                          u'|', u'!', u'[', u'<<', u'(', u'E', u',', u'F', u')', u'$',
                          u'G', u']'])

    def test_tokenize_link_types(self):
        '''
        Test tokenization of basic link types.
        '''
        self.assertEqual(tgrep.tgrep_tokenize(u'A<B'),     [u'A', u'<', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>B'),     [u'A', u'>', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<3B'),    [u'A', u'<3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>3B'),    [u'A', u'>3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<,B'),    [u'A', u'<,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>,B'),    [u'A', u'>,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<-3B'),   [u'A', u'<-3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>-3B'),   [u'A', u'>-3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<-B'),    [u'A', u'<-', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>-B'),    [u'A', u'>-', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<\'B'),   [u'A', u'<\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>\'B'),   [u'A', u'>\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<:B'),    [u'A', u'<:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>:B'),    [u'A', u'>:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<<B'),    [u'A', u'<<', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>>B'),    [u'A', u'>>', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<<,B'),   [u'A', u'<<,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>>,B'),   [u'A', u'>>,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<<\'B'),  [u'A', u'<<\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>>\'B'),  [u'A', u'>>\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<<:B'),   [u'A', u'<<:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A>>:B'),   [u'A', u'>>:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A.B'),     [u'A', u'.', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A,B'),     [u'A', u',', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A..B'),    [u'A', u'..', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A,,B'),    [u'A', u',,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A$B'),     [u'A', u'$', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A$.B'),    [u'A', u'$.', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A$,B'),    [u'A', u'$,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A$..B'),   [u'A', u'$..', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A$,,B'),   [u'A', u'$,,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<B'),    [u'A', u'!', u'<', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>B'),    [u'A', u'!', u'>', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<3B'),   [u'A', u'!', u'<3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>3B'),   [u'A', u'!', u'>3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<,B'),   [u'A', u'!', u'<,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>,B'),   [u'A', u'!', u'>,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<-3B'),
                         [u'A', u'!', u'<-3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>-3B'),
                         [u'A', u'!', u'>-3', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<-B'),   [u'A', u'!', u'<-', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>-B'),   [u'A', u'!', u'>-', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<\'B'),
                         [u'A', u'!', u'<\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>\'B'),
                         [u'A', u'!', u'>\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<:B'),   [u'A', u'!', u'<:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>:B'),   [u'A', u'!', u'>:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<<B'),   [u'A', u'!', u'<<', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>>B'),   [u'A', u'!', u'>>', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<<,B'),
                         [u'A', u'!', u'<<,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>>,B'),
                         [u'A', u'!', u'>>,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<<\'B'),
                         [u'A', u'!', u'<<\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>>\'B'),
                         [u'A', u'!', u'>>\'', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!<<:B'),
                         [u'A', u'!', u'<<:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!>>:B'),
                         [u'A', u'!', u'>>:', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!.B'),    [u'A', u'!', u'.', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!,B'),    [u'A', u'!', u',', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!..B'),   [u'A', u'!', u'..', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!,,B'),   [u'A', u'!', u',,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!$B'),    [u'A', u'!', u'$', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!$.B'),   [u'A', u'!', u'$.', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!$,B'),   [u'A', u'!', u'$,', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!$..B'),
                         [u'A', u'!', u'$..', u'B'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A!$,,B'),
                         [u'A', u'!', u'$,,', u'B'])

    def test_tokenize_examples(self):
        '''
        Test tokenization of the TGrep2 manual example patterns.
        '''
        self.assertEqual(tgrep.tgrep_tokenize(u'NP < PP'),
                         [u'NP', u'<', u'PP'])
        self.assertEqual(tgrep.tgrep_tokenize(u'/^NP/'),
                         [u'/^NP/'])
        self.assertEqual(tgrep.tgrep_tokenize(u'NP << PP . VP'),
                         [u'NP', u'<<', u'PP', u'.', u'VP'])
        self.assertEqual(tgrep.tgrep_tokenize(u'NP << PP | . VP'),
                         [u'NP', u'<<', u'PP', u'|', u'.', u'VP'])
        self.assertEqual(tgrep.tgrep_tokenize(u'NP !<< PP [> NP | >> VP]'),
                         [u'NP', u'!', u'<<', u'PP', u'[', u'>', u'NP', u'|',
                          u'>>', u'VP', u']'])
        self.assertEqual(tgrep.tgrep_tokenize(u'NP << (PP . VP)'),
                         [u'NP', u'<<', u'(', u'PP', u'.', u'VP', u')'])
        self.assertEqual(tgrep.tgrep_tokenize(u'NP <\' (PP <, (IN < on))'),
                         [u'NP', u'<\'', u'(', u'PP', u'<,', u'(', u'IN', u'<',
                          u'on', u')', u')'])
        self.assertEqual(tgrep.tgrep_tokenize(u'S < (A < B) < C'),
                         [u'S', u'<', u'(', u'A', u'<', u'B', u')', u'<', u'C'])
        self.assertEqual(tgrep.tgrep_tokenize(u'S < ((A < B) < C)'),
                         [u'S', u'<', u'(', u'(', u'A', u'<', u'B', u')',
                          u'<', u'C', u')'])
        self.assertEqual(tgrep.tgrep_tokenize(u'S < (A < B < C)'),
                         [u'S', u'<', u'(', u'A', u'<', u'B', u'<', u'C', u')'])
        self.assertEqual(tgrep.tgrep_tokenize(u'A<B&.C'),
                         [u'A', u'<', u'B', u'&', u'.', u'C'])

    def test_tokenize_quoting(self):
        '''
        Test tokenization of quoting.
        '''
        self.assertEqual(tgrep.tgrep_tokenize('"A<<:B"<<:"A $.. B"<"A>3B"<C'),
                         ['"A<<:B"', u'<<:', u'"A $.. B"', u'<', u'"A>3B"',
                          '<', u'C'])

    def test_tokenize_nodenames(self):
        '''
        Test tokenization of node names.
        '''
        self.assertEqual(tgrep.tgrep_tokenize(u'Robert'), [u'Robert'])
        self.assertEqual(tgrep.tgrep_tokenize(u'/^[Bb]ob/'), [u'/^[Bb]ob/'])
        self.assertEqual(tgrep.tgrep_tokenize(u'*'), [u'*'])
        self.assertEqual(tgrep.tgrep_tokenize(u'__'), [u'__'])
        # test tokenization of NLTK tree position syntax
        self.assertEqual(tgrep.tgrep_tokenize(u'N()'),
                         [u'N(', u')'])
        self.assertEqual(tgrep.tgrep_tokenize(u'N(0,)'),
                         [u'N(', u'0', u',', u')'])
        self.assertEqual(tgrep.tgrep_tokenize(u'N(0,0)'),
                         [u'N(', u'0', u',', u'0', u')'])
        self.assertEqual(tgrep.tgrep_tokenize(u'N(0,0,)'),
                         [u'N(', u'0', u',', u'0', u',', u')'])

    def test_node_simple(self):
        '''
        Test a simple use of tgrep for finding nodes matching a given
        pattern.
        '''
        tree = ParentedTree.fromstring(
            u'(S (NP (DT the) (JJ big) (NN dog)) '
            u'(VP bit) (NP (DT a) (NN cat)))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'NN'),
                         [(0,2), (2,1)])
        self.assertEqual(tgrep.tgrep_nodes(tree, u'NN'),
                         [tree[0,2], tree[2,1]])
        self.assertEqual(tgrep.tgrep_positions(tree, u'NN|JJ'),
                         [(0, 1), (0, 2), (2, 1)])

    def test_node_regex(self):
        '''
        Test regex matching on nodes.
        '''
        tree = ParentedTree.fromstring(u'(S (NP-SBJ x) (NP x) (NNP x) (VP x))')
        # This is a regular expression that matches any node whose
        # name starts with NP, including NP-SBJ:
        self.assertEqual(tgrep.tgrep_positions(tree, u'/^NP/'),
                         [(0,), (1,)])

    def test_node_tree_position(self):
        '''
        Test matching on nodes based on NLTK tree position.
        '''
        tree = ParentedTree.fromstring(u'(S (NP-SBJ x) (NP x) (NNP x) (VP x))')
        # test all tree positions that are not leaves
        leaf_positions = set([tree.leaf_treeposition(x)
                              for x in range(len(tree.leaves()))])
        tree_positions = [x for x in tree.treepositions()
                          if x not in leaf_positions]
        for position in tree_positions:
            node_id = u'N{0}'.format(position)
            tgrep_positions = tgrep.tgrep_positions(tree, node_id)
            self.assertEqual(len(tgrep_positions), 1)
            self.assertEqual(tgrep_positions[0], position)

    def tests_rel_dominance(self):
        '''
        Test matching nodes based on dominance relations.
        '''
        tree = ParentedTree.fromstring(u'(S (A (T x)) (B (N x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* < T'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* < T > S'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !< T'),
                         [(), (0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !< T > S'),
                         [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* > A'),
                         [(0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* > B'),
                         [(1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !> B'),
                         [(), (0,), (0, 0), (0, 0, 0), (1,), (1, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !> B >> S'),
                         [(0,), (0, 0), (1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >> S'),
                         [(0,), (0, 0), (1,), (1, 0)])
        # Known issue:
        #self.assertEqual(tgrep.tgrep_positions(tree, u'* !>> S'),
        #                 [()])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* << T'),
                         [(), (0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !<< T'),
                         [(0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0)])
        tree = ParentedTree.fromstring(u'(S (A (T x)) (B (T x) (N x )))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <: T'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* < T'),
                         [(0,), (1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !<: T'),
                         [(), (0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0),
                          (1, 1), (1, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !<: T > S'),
                         [(1,)])
        tree = ParentedTree.fromstring(u'(S (T (A x) (B x)) (T (C x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >: T'),
                         [(1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* !>: T'),
                         [(), (0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0),
                          (1,), (1, 0, 0)])
        tree = ParentedTree.fromstring(u'(S (A (B (C (D (E (T x))))))'
                                       u' (A (B (C (D (E (T x))) (N x)))))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <<: T'),
                         [(0,), (0, 0), (0, 0, 0), (0, 0, 0, 0),
                          (0, 0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >>: A'),
                         [(0, 0), (0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0, 0),
                          (0, 0, 0, 0, 0, 0), (1, 0), (1, 0, 0)])

    def test_rel_sister_nodes(self):
        '''
        Test matching sister nodes in a tree.
        '''
        tree = ParentedTree.fromstring(u'(S (A x) (B x) (C x))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* $. B'),  [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* $.. B'), [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* $, B'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* $,, B'), [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* $ B'),   [(0,), (2,)])

    def tests_rel_indexed_children(self):
        '''
        Test matching nodes based on their index in their parent node.
        '''
        tree = ParentedTree.fromstring(u'(S (A x) (B x) (C x))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >, S'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >1 S'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >2 S'),   [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >3 S'),   [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >\' S'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >-1 S'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >-2 S'),  [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* >-3 S'),  [(0,)])
        tree = ParentedTree.fromstring(
            u'(S (D (A x) (B x) (C x)) (E (B x) (C x) (A x)) '
            u'(F (C x) (A x) (B x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <, A'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <1 A'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <2 A'),   [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <3 A'),   [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <\' A'),  [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <-1 A'),  [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <-2 A'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* <-3 A'),  [(0,)])

    def test_rel_precedence(self):
        '''
        Test matching nodes based on precedence relations.
        '''
        tree = ParentedTree.fromstring(u'(S (NP (NP (PP x)) (NP (AP x)))'
                                       u' (VP (AP (X (PP x)) (Y (AP x))))'
                                       u' (NP (RC (NP (AP x)))))')
        self.assertEqual(tgrep.tgrep_positions(tree, u'* . X'),
                         [(0,), (0, 1), (0, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* . Y'),
                         [(1, 0, 0), (1, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* .. X'),
                         [(0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* .. Y'),
                         [(0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0),
                          (1, 0, 0), (1, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* , X'),
                         [(1, 0, 1), (1, 0, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* , Y'),
                         [(2,), (2, 0), (2, 0, 0), (2, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* ,, X'),
                         [(1, 0, 1), (1, 0, 1, 0), (2,), (2, 0), (2, 0, 0),
                          (2, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, u'* ,, Y'),
                         [(2,), (2, 0), (2, 0, 0), (2, 0, 0, 0)])

    def test_examples(self):
        '''
        Test the Basic Examples from the TGrep2 manual.
        '''
        tree = ParentedTree.fromstring(u'(S (NP (AP x)) (NP (PP x)))')
        # This matches any NP node that immediately dominates a PP:
        self.assertEqual(tgrep.tgrep_positions(tree, u'NP < PP'),
                         [(1,)])

        tree = ParentedTree.fromstring(u'(S (NP x) (VP x) (NP (PP x)) (VP x))')
        # This matches an NP that dominates a PP and is immediately
        # followed by a VP:
        self.assertEqual(tgrep.tgrep_positions(tree, u'NP << PP . VP'),
                         [(2,)])

        tree = ParentedTree.fromstring(u'(S (NP (AP x)) (NP (PP x)) '
                                       u'(NP (DET x) (NN x)) (VP x))')
        # This matches an NP that dominates a PP or is immediately
        # followed by a VP:
        self.assertEqual(tgrep.tgrep_positions(tree, u'NP << PP | . VP'),
                         [(1,), (2,)])

        tree = ParentedTree.fromstring(u'(S (NP (NP (PP x)) (NP (AP x)))'
                                       u' (VP (AP (NP (PP x)) (NP (AP x))))'
                                       u' (NP (RC (NP (AP x)))))')
        # This matches an NP that does not dominate a PP. Also, the NP
        # must either have a parent that is an NP or be dominated by a
        # VP:
        self.assertEqual(tgrep.tgrep_positions(tree,
                                               u'NP !<< PP [> NP | >> VP]'),
                         [(0, 1), (1, 0, 1)])

        tree = ParentedTree.fromstring(u'(S (NP (AP (PP x) (VP x))) '
                                       u'(NP (AP (PP x) (NP x))) (NP x))')
        # This matches an NP that dominates a PP which itself is
        # immediately followed by a VP. Note the use of parentheses to
        # group ". VP" with the PP rather than with the NP:
        self.assertEqual(tgrep.tgrep_positions(tree, u'NP << (PP . VP)'),
                         [(0,)])

        tree = ParentedTree.fromstring(
            u'(S (NP (DET a) (NN cat) (PP (IN on) (NP x)))'
            u' (NP (DET a) (NN cat) (PP (IN on) (NP x)) (PP x))'
            u' (NP x))')
        # This matches an NP whose last child is a PP that begins with
        # the preposition "on":
        self.assertEqual(tgrep.tgrep_positions(tree,
                                               u'NP <\' (PP <, (IN < on))'),
                         [(0,)])

        tree = ParentedTree.fromstring(
            u'(S (S (C x) (A (B x))) (S (C x) (A x)) '
            u'(S (D x) (A (B x))))')
        # The following pattern matches an S which has a child A and
        # another child that is a C and that the A has a child B:
        self.assertEqual(tgrep.tgrep_positions(tree, u'S < (A < B) < C'),
                         [(0,)])

        tree = ParentedTree.fromstring(
            u'(S (S (A (B x) (C x))) (S (S (C x) (A (B x)))))')
        # However, this pattern means that S has child A and that A
        # has children B and C:
        self.assertEqual(tgrep.tgrep_positions(tree, u'S < ((A < B) < C)'),
                         [(0,)])

        # It is equivalent to this:
        self.assertEqual(tgrep.tgrep_positions(tree, u'S < (A < B < C)'),
                         [(0,)])

if __name__ == u'__main__':
    unittest.main()
