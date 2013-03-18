#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Unit tests for TGrep search implementation for NTLK ParentedTrees.

(c) 16 March, 2013 Will Roberts
'''

from nltk.tree import ParentedTree
import sys
import tgrep
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
        self.assertEqual(tgrep.tgrep_positions(tree, '* !>> S'),
                         [()])
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

if __name__ == '__main__' and sys.argv != ['']:
    unittest.main()

