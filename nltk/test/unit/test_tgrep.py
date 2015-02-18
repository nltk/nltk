#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Unit tests for TGrep search implementation for NTLK ParentedTrees.

(c) 16 March, 2013 Will Roberts
'''

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
        tokens = tgrep.tgrep_tokenize('A .. (B !< C . D) | ![<< (E , F) $ G]')
        self.assertEqual(tokens,
                         ['A', '..', '(', 'B', '!', '<', 'C', '.', 'D', ')',
                          '|', '!', '[', '<<', '(', 'E', ',', 'F', ')', '$',
                          'G', ']'])

    def test_tokenize_link_types(self):
        '''
        Test tokenization of basic link types.
        '''
        self.assertEqual(tgrep.tgrep_tokenize('A<B'),     ['A', '<', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>B'),     ['A', '>', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<3B'),    ['A', '<3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>3B'),    ['A', '>3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<,B'),    ['A', '<,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>,B'),    ['A', '>,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<-3B'),   ['A', '<-3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>-3B'),   ['A', '>-3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<-B'),    ['A', '<-', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>-B'),    ['A', '>-', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<\'B'),   ['A', '<\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>\'B'),   ['A', '>\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<:B'),    ['A', '<:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>:B'),    ['A', '>:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<<B'),    ['A', '<<', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>>B'),    ['A', '>>', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<<,B'),   ['A', '<<,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>>,B'),   ['A', '>>,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<<\'B'),  ['A', '<<\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>>\'B'),  ['A', '>>\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A<<:B'),   ['A', '<<:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A>>:B'),   ['A', '>>:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A.B'),     ['A', '.', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A,B'),     ['A', ',', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A..B'),    ['A', '..', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A,,B'),    ['A', ',,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A$B'),     ['A', '$', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A$.B'),    ['A', '$.', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A$,B'),    ['A', '$,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A$..B'),   ['A', '$..', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A$,,B'),   ['A', '$,,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<B'),    ['A', '!', '<', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>B'),    ['A', '!', '>', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<3B'),   ['A', '!', '<3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>3B'),   ['A', '!', '>3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<,B'),   ['A', '!', '<,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>,B'),   ['A', '!', '>,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<-3B'),
                         ['A', '!', '<-3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>-3B'),
                         ['A', '!', '>-3', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<-B'),   ['A', '!', '<-', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>-B'),   ['A', '!', '>-', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<\'B'),
                         ['A', '!', '<\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>\'B'),
                         ['A', '!', '>\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<:B'),   ['A', '!', '<:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>:B'),   ['A', '!', '>:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<<B'),   ['A', '!', '<<', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>>B'),   ['A', '!', '>>', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<<,B'),
                         ['A', '!', '<<,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>>,B'),
                         ['A', '!', '>>,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<<\'B'),
                         ['A', '!', '<<\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>>\'B'),
                         ['A', '!', '>>\'', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!<<:B'),
                         ['A', '!', '<<:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!>>:B'),
                         ['A', '!', '>>:', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!.B'),    ['A', '!', '.', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!,B'),    ['A', '!', ',', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!..B'),   ['A', '!', '..', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!,,B'),   ['A', '!', ',,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!$B'),    ['A', '!', '$', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!$.B'),   ['A', '!', '$.', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!$,B'),   ['A', '!', '$,', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!$..B'),
                         ['A', '!', '$..', 'B'])
        self.assertEqual(tgrep.tgrep_tokenize('A!$,,B'),
                         ['A', '!', '$,,', 'B'])

    def test_tokenize_examples(self):
        '''
        Test tokenization of the TGrep2 manual example patterns.
        '''
        self.assertEqual(tgrep.tgrep_tokenize('NP < PP'),
                         ['NP', '<', 'PP'])
        self.assertEqual(tgrep.tgrep_tokenize('/^NP/'),
                         ['/^NP/'])
        self.assertEqual(tgrep.tgrep_tokenize('NP << PP . VP'),
                         ['NP', '<<', 'PP', '.', 'VP'])
        self.assertEqual(tgrep.tgrep_tokenize('NP << PP | . VP'),
                         ['NP', '<<', 'PP', '|', '.', 'VP'])
        self.assertEqual(tgrep.tgrep_tokenize('NP !<< PP [> NP | >> VP]'),
                         ['NP', '!', '<<', 'PP', '[', '>', 'NP', '|',
                          '>>', 'VP', ']'])
        self.assertEqual(tgrep.tgrep_tokenize('NP << (PP . VP)'),
                         ['NP', '<<', '(', 'PP', '.', 'VP', ')'])
        self.assertEqual(tgrep.tgrep_tokenize('NP <\' (PP <, (IN < on))'),
                         ['NP', '<\'', '(', 'PP', '<,', '(', 'IN', '<',
                          'on', ')', ')'])
        self.assertEqual(tgrep.tgrep_tokenize('S < (A < B) < C'),
                         ['S', '<', '(', 'A', '<', 'B', ')', '<', 'C'])
        self.assertEqual(tgrep.tgrep_tokenize('S < ((A < B) < C)'),
                         ['S', '<', '(', '(', 'A', '<', 'B', ')',
                          '<', 'C', ')'])
        self.assertEqual(tgrep.tgrep_tokenize('S < (A < B < C)'),
                         ['S', '<', '(', 'A', '<', 'B', '<', 'C', ')'])
        self.assertEqual(tgrep.tgrep_tokenize('A<B&.C'),
                         ['A', '<', 'B', '&', '.', 'C'])

    def test_tokenize_quoting(self):
        '''
        Test tokenization of quoting.
        '''
        self.assertEqual(tgrep.tgrep_tokenize('"A<<:B"<<:"A $.. B"<"A>3B"<C'),
                         ['"A<<:B"', '<<:', '"A $.. B"', '<', '"A>3B"',
                          '<', 'C'])

    def test_tokenize_nodenames(self):
        '''
        Test tokenization of node names.
        '''
        self.assertEqual(tgrep.tgrep_tokenize('Robert'), ['Robert'])
        self.assertEqual(tgrep.tgrep_tokenize('/^[Bb]ob/'), ['/^[Bb]ob/'])
        self.assertEqual(tgrep.tgrep_tokenize('*'), ['*'])
        self.assertEqual(tgrep.tgrep_tokenize('__'), ['__'])
        # test tokenization of NLTK tree position syntax
        self.assertEqual(tgrep.tgrep_tokenize('N()'),
                         ['N(', ')'])
        self.assertEqual(tgrep.tgrep_tokenize('N(0,)'),
                         ['N(', '0', ',', ')'])
        self.assertEqual(tgrep.tgrep_tokenize('N(0,0)'),
                         ['N(', '0', ',', '0', ')'])
        self.assertEqual(tgrep.tgrep_tokenize('N(0,0,)'),
                         ['N(', '0', ',', '0', ',', ')'])

    def test_node_simple(self):
        '''
        Test a simple use of tgrep for finding nodes matching a given
        pattern.
        '''
        tree = ParentedTree('(S (NP (DT the) (JJ big) (NN dog)) '
                         '(VP bit) (NP (DT a) (NN cat)))')
        self.assertEqual(tgrep.tgrep_positions(tree, 'NN'),
                         [(0,2), (2,1)])
        self.assertEqual(tgrep.tgrep_nodes(tree, 'NN'),
                         [tree[0,2], tree[2,1]])
        self.assertEqual(tgrep.tgrep_positions(tree, 'NN|JJ'),
                         [(0, 1), (0, 2), (2, 1)])

    def test_node_regex(self):
        '''
        Test regex matching on nodes.
        '''
        tree = ParentedTree('(S (NP-SBJ x) (NP x) (NNP x) (VP x))')
        # This is a regular expression that matches any node whose
        # name starts with NP, including NP-SBJ:
        self.assertEqual(tgrep.tgrep_positions(tree, '/^NP/'),
                         [(0,), (1,)])

    def test_node_tree_position(self):
        '''
        Test matching on nodes based on NLTK tree position.
        '''
        tree = ParentedTree('(S (NP-SBJ x) (NP x) (NNP x) (VP x))')
        # test all tree positions that are not leaves
        leaf_positions = set([tree.leaf_treeposition(x)
                              for x in range(len(tree.leaves()))])
        tree_positions = [x for x in tree.treepositions()
                          if x not in leaf_positions]
        for position in tree_positions:
            node_id = 'N{0}'.format(position)
            tgrep_positions = tgrep.tgrep_positions(tree, node_id)
            self.assertEqual(len(tgrep_positions), 1)
            self.assertEqual(tgrep_positions[0], position)

    def tests_rel_dominance(self):
        '''
        Test matching nodes based on dominance relations.
        '''
        tree = ParentedTree('(S (A (T x)) (B (N x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* < T'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* < T > S'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !< T'),
                         [(), (0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !< T > S'),
                         [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* > A'),
                         [(0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* > B'),
                         [(1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !> B'),
                         [(), (0,), (0, 0), (0, 0, 0), (1,), (1, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !> B >> S'),
                         [(0,), (0, 0), (1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >> S'),
                         [(0,), (0, 0), (1,), (1, 0)])
        # Known issue:
        #self.assertEqual(tgrep.tgrep_positions(tree, '* !>> S'),
        #                 [()])
        self.assertEqual(tgrep.tgrep_positions(tree, '* << T'),
                         [(), (0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !<< T'),
                         [(0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0)])
        tree = ParentedTree('(S (A (T x)) (B (T x) (N x )))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* <: T'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* < T'),
                         [(0,), (1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !<: T'),
                         [(), (0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0),
                          (1, 1), (1, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !<: T > S'),
                         [(1,)])
        tree = ParentedTree('(S (T (A x) (B x)) (T (C x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* >: T'),
                         [(1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !>: T'),
                         [(), (0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0),
                          (1,), (1, 0, 0)])
        tree = ParentedTree('(S (A (B (C (D (E (T x))))))'
                            ' (A (B (C (D (E (T x))) (N x)))))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* <<: T'),
                         [(0,), (0, 0), (0, 0, 0), (0, 0, 0, 0),
                          (0, 0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >>: A'),
                         [(0, 0), (0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0, 0),
                          (0, 0, 0, 0, 0, 0), (1, 0), (1, 0, 0)])

    def test_rel_sister_nodes(self):
        '''
        Test matching sister nodes in a tree.
        '''
        tree = ParentedTree('(S (A x) (B x) (C x))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* $. B'),  [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $.. B'), [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $, B'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $,, B'), [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $ B'),   [(0,), (2,)])

    def tests_rel_indexed_children(self):
        '''
        Test matching nodes based on their index in their parent node.
        '''
        tree = ParentedTree('(S (A x) (B x) (C x))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* >, S'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >1 S'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >2 S'),   [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >3 S'),   [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >\' S'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >-1 S'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >-2 S'),  [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >-3 S'),  [(0,)])
        tree = ParentedTree('(S (D (A x) (B x) (C x)) (E (B x) (C x) (A x)) '
                            '(F (C x) (A x) (B x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* <, A'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <1 A'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <2 A'),   [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <3 A'),   [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <\' A'),  [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <-1 A'),  [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <-2 A'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <-3 A'),  [(0,)])

    def test_rel_precedence(self):
        '''
        Test matching nodes based on precedence relations.
        '''
        tree = ParentedTree('(S (NP (NP (PP x)) (NP (AP x)))'
                            ' (VP (AP (X (PP x)) (Y (AP x))))'
                            ' (NP (RC (NP (AP x)))))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* . X'),
                         [(0,), (0, 1), (0, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* . Y'),
                         [(1, 0, 0), (1, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* .. X'),
                         [(0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* .. Y'),
                         [(0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0),
                          (1, 0, 0), (1, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* , X'),
                         [(1, 0, 1), (1, 0, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* , Y'),
                         [(2,), (2, 0), (2, 0, 0), (2, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* ,, X'),
                         [(1, 0, 1), (1, 0, 1, 0), (2,), (2, 0), (2, 0, 0),
                          (2, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* ,, Y'),
                         [(2,), (2, 0), (2, 0, 0), (2, 0, 0, 0)])

    def test_examples(self):
        '''
        Test the Basic Examples from the TGrep2 manual.
        '''
        tree = ParentedTree('(S (NP (AP x)) (NP (PP x)))')
        # This matches any NP node that immediately dominates a PP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP < PP'),
                         [(1,)])

        tree = ParentedTree('(S (NP x) (VP x) (NP (PP x)) (VP x))')
        # This matches an NP that dominates a PP and is immediately
        # followed by a VP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP << PP . VP'),
                         [(2,)])

        tree = ParentedTree('(S (NP (AP x)) (NP (PP x)) '
                            '(NP (DET x) (NN x)) (VP x))')
        # This matches an NP that dominates a PP or is immediately
        # followed by a VP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP << PP | . VP'),
                         [(1,), (2,)])

        tree = ParentedTree('(S (NP (NP (PP x)) (NP (AP x)))'
                            ' (VP (AP (NP (PP x)) (NP (AP x))))'
                            ' (NP (RC (NP (AP x)))))')
        # This matches an NP that does not dominate a PP. Also, the NP
        # must either have a parent that is an NP or be dominated by a
        # VP:
        self.assertEqual(tgrep.tgrep_positions(tree,
                                               'NP !<< PP [> NP | >> VP]'),
                         [(0, 1), (1, 0, 1)])

        tree = ParentedTree('(S (NP (AP (PP x) (VP x))) '
                            '(NP (AP (PP x) (NP x))) (NP x))')
        # This matches an NP that dominates a PP which itself is
        # immediately followed by a VP. Note the use of parentheses to
        # group ". VP" with the PP rather than with the NP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP << (PP . VP)'),
                         [(0,)])

        tree = ParentedTree('(S (NP (DET a) (NN cat) (PP (IN on) (NP x)))'
                            ' (NP (DET a) (NN cat) (PP (IN on) (NP x)) (PP x))'
                            ' (NP x))')
        # This matches an NP whose last child is a PP that begins with
        # the preposition "on":
        self.assertEqual(tgrep.tgrep_positions(tree,
                                               'NP <\' (PP <, (IN < on))'),
                         [(0,)])

        tree = ParentedTree('(S (S (C x) (A (B x))) (S (C x) (A x)) '
                            '(S (D x) (A (B x))))')
        # The following pattern matches an S which has a child A and
        # another child that is a C and that the A has a child B:
        self.assertEqual(tgrep.tgrep_positions(tree, 'S < (A < B) < C'),
                         [(0,)])

        tree = ParentedTree('(S (S (A (B x) (C x))) (S (S (C x) (A (B x)))))')
        # However, this pattern means that S has child A and that A
        # has children B and C:
        self.assertEqual(tgrep.tgrep_positions(tree, 'S < ((A < B) < C)'),
                         [(0,)])

        # It is equivalent to this:
        self.assertEqual(tgrep.tgrep_positions(tree, 'S < (A < B < C)'),
                         [(0,)])

if __name__ == '__main__':
    unittest.main()
