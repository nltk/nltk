#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Natural Language Toolkit: TGrep search
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Will Roberts <wildwilhelm@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

'''
Unit tests for nltk.tgrep.
'''

from __future__ import absolute_import, print_function, unicode_literals
from nltk.compat import b
from nltk.tree import ParentedTree
from nltk import tgrep
import unittest

class TestSequenceFunctions(unittest.TestCase):

    '''
    Class containing unit tests for nltk.tgrep.
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

    def test_tokenize_encoding(self):
        '''
        Test that tokenization handles bytes and strs the same way.
        '''
        self.assertEqual(
            tgrep.tgrep_tokenize(b('A .. (B !< C . D) | ![<< (E , F) $ G]')),
            tgrep.tgrep_tokenize('A .. (B !< C . D) | ![<< (E , F) $ G]'))

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

    def test_tokenize_macros(self):
        '''
        Test tokenization of macro definitions.
        '''
        self.assertEqual(tgrep.tgrep_tokenize(
            '@ NP /^NP/;\n@ NN /^NN/;\n@NP [!< NP | < @NN] !$.. @NN'),
                         ['@', 'NP', '/^NP/', ';', '@', 'NN', '/^NN/', ';',
                          '@NP', '[', '!', '<', 'NP', '|', '<', '@NN', ']',
                          '!', '$..', '@NN'])

    def test_node_simple(self):
        '''
        Test a simple use of tgrep for finding nodes matching a given
        pattern.
        '''
        tree = ParentedTree.fromstring(
            '(S (NP (DT the) (JJ big) (NN dog)) '
            '(VP bit) (NP (DT a) (NN cat)))')
        self.assertEqual(tgrep.tgrep_positions(tree, 'NN'),
                         [(0,2), (2,1)])
        self.assertEqual(tgrep.tgrep_nodes(tree, 'NN'),
                         [tree[0,2], tree[2,1]])
        self.assertEqual(tgrep.tgrep_positions(tree, 'NN|JJ'),
                         [(0, 1), (0, 2), (2, 1)])

    def test_node_printing(self):
        '''Test that the tgrep print operator ' is properly ignored.'''
        tree = ParentedTree.fromstring('(S (n x) (N x))')
        self.assertEqual(tgrep.tgrep_positions(tree, 'N'),
                         tgrep.tgrep_positions(tree, '\'N'))
        self.assertEqual(tgrep.tgrep_positions(tree, '/[Nn]/'),
                         tgrep.tgrep_positions(tree, '\'/[Nn]/'))

    def test_node_encoding(self):
        '''
        Test that tgrep search strings handles bytes and strs the same
        way.
        '''
        tree = ParentedTree.fromstring(
            '(S (NP (DT the) (JJ big) (NN dog)) '
            '(VP bit) (NP (DT a) (NN cat)))')
        self.assertEqual(tgrep.tgrep_positions(tree, b('NN')),
                         tgrep.tgrep_positions(tree, 'NN'))
        self.assertEqual(tgrep.tgrep_nodes(tree, b('NN')),
                         tgrep.tgrep_nodes(tree, 'NN'))
        self.assertEqual(tgrep.tgrep_positions(tree, b('NN|JJ')),
                         tgrep.tgrep_positions(tree, 'NN|JJ'))

    def test_node_nocase(self):
        '''
        Test selecting nodes using case insensitive node names.
        '''
        tree = ParentedTree.fromstring('(S (n x) (N x))')
        self.assertEqual(tgrep.tgrep_positions(tree, '"N"'), [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, 'i@"N"'), [(0,), (1,)])

    def test_node_quoted(self):
        '''
        Test selecting nodes using quoted node names.
        '''
        tree = ParentedTree.fromstring('(N ("N" x) (N" x) ("\\" x))')
        self.assertEqual(tgrep.tgrep_positions(tree, '"N"'), [()])
        self.assertEqual(tgrep.tgrep_positions(tree, '"\\"N\\""'), [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '"N\\""'), [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '"\\"\\\\\\""'), [(2,)])

    def test_node_regex(self):
        '''
        Test regex matching on nodes.
        '''
        tree = ParentedTree.fromstring('(S (NP-SBJ x) (NP x) (NNP x) (VP x))')
        # This is a regular expression that matches any node whose
        # name starts with NP, including NP-SBJ:
        self.assertEqual(tgrep.tgrep_positions(tree, '/^NP/'),
                         [(0,), (1,)])

    def test_node_regex_2(self):
        '''
        Test regex matching on nodes.
        '''
        tree = ParentedTree.fromstring('(S (SBJ x) (SBJ1 x) (NP-SBJ x))')
        self.assertEqual(tgrep.tgrep_positions(tree, '/^SBJ/'),
                         [(0,), (1,)])
        # This is a regular expression that matches any node whose
        # name includes SBJ, including NP-SBJ:
        self.assertEqual(tgrep.tgrep_positions(tree, '/SBJ/'),
                         [(0,), (1,), (2,)])

    def test_node_tree_position(self):
        '''
        Test matching on nodes based on NLTK tree position.
        '''
        tree = ParentedTree.fromstring('(S (NP-SBJ x) (NP x) (NNP x) (VP x))')
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

    def test_node_noleaves(self):
        '''
        Test node name matching with the search_leaves flag set to False.
        '''
        tree = ParentedTree.fromstring('(S (A (T x)) (B (N x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, 'x'),
                         [(0, 0, 0), (1, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, 'x', False),
                         [])

    def tests_rel_dominance(self):
        '''
        Test matching nodes based on dominance relations.
        '''
        tree = ParentedTree.fromstring('(S (A (T x)) (B (N x)))')
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
        self.assertEqual(tgrep.tgrep_positions(tree, '* >>, S'),
                         [(0,), (0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >>\' S'),
                         [(1,), (1, 0)])
        # Known issue:
        #self.assertEqual(tgrep.tgrep_positions(tree, '* !>> S'),
        #                 [()])
        self.assertEqual(tgrep.tgrep_positions(tree, '* << T'),
                         [(), (0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <<\' T'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* <<1 N'),
                         [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !<< T'),
                         [(0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0)])
        tree = ParentedTree.fromstring('(S (A (T x)) (B (T x) (N x )))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* <: T'),
                         [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* < T'),
                         [(0,), (1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !<: T'),
                         [(), (0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0),
                          (1, 1), (1, 1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !<: T > S'),
                         [(1,)])
        tree = ParentedTree.fromstring('(S (T (A x) (B x)) (T (C x)))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* >: T'),
                         [(1, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* !>: T'),
                         [(), (0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0),
                          (1,), (1, 0, 0)])
        tree = ParentedTree.fromstring('(S (A (B (C (D (E (T x))))))'
                                       ' (A (B (C (D (E (T x))) (N x)))))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* <<: T'),
                         [(0,), (0, 0), (0, 0, 0), (0, 0, 0, 0),
                          (0, 0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0, 0)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >>: A'),
                         [(0, 0), (0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0, 0),
                          (0, 0, 0, 0, 0, 0), (1, 0), (1, 0, 0)])

    def test_bad_operator(self):
        '''
        Test error handling of undefined tgrep operators.
        '''
        tree = ParentedTree.fromstring('(S (A (T x)) (B (N x)))')
        self.assertRaises(
            tgrep.TgrepException,
            tgrep.tgrep_positions,
            tree, '* >>> S')

    def test_comments(self):
        '''
        Test that comments are correctly filtered out of tgrep search
        strings.
        '''
        tree = ParentedTree.fromstring('(S (NN x) (NP x) (NN x))')
        search1 = '''
        @ NP /^NP/;
        @ NN /^NN/;
        @NN
        '''
        self.assertEqual(tgrep.tgrep_positions(tree, search1),
                         [(0,), (2,)])
        search2 = '''
        # macros
        @ NP /^NP/;
        @ NN /^NN/;

        # search string
        @NN
        '''
        self.assertEqual(tgrep.tgrep_positions(tree, search2),
                         [(0,), (2,)])

    def test_rel_sister_nodes(self):
        '''
        Test matching sister nodes in a tree.
        '''
        tree = ParentedTree.fromstring('(S (A x) (B x) (C x))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* $. B'),  [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $.. B'), [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $, B'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $,, B'), [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* $ B'),   [(0,), (2,)])

    def tests_rel_indexed_children(self):
        '''
        Test matching nodes based on their index in their parent node.
        '''
        tree = ParentedTree.fromstring('(S (A x) (B x) (C x))')
        self.assertEqual(tgrep.tgrep_positions(tree, '* >, S'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >1 S'),   [(0,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >2 S'),   [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >3 S'),   [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >\' S'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >-1 S'),  [(2,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >-2 S'),  [(1,)])
        self.assertEqual(tgrep.tgrep_positions(tree, '* >-3 S'),  [(0,)])
        tree = ParentedTree.fromstring(
            '(S (D (A x) (B x) (C x)) (E (B x) (C x) (A x)) '
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
        tree = ParentedTree.fromstring('(S (NP (NP (PP x)) (NP (AP x)))'
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
        tree = ParentedTree.fromstring('(S (NP (AP x)) (NP (PP x)))')
        # This matches any NP node that immediately dominates a PP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP < PP'),
                         [(1,)])

        tree = ParentedTree.fromstring('(S (NP x) (VP x) (NP (PP x)) (VP x))')
        # This matches an NP that dominates a PP and is immediately
        # followed by a VP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP << PP . VP'),
                         [(2,)])

        tree = ParentedTree.fromstring('(S (NP (AP x)) (NP (PP x)) '
                                       '(NP (DET x) (NN x)) (VP x))')
        # This matches an NP that dominates a PP or is immediately
        # followed by a VP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP << PP | . VP'),
                         [(1,), (2,)])

        tree = ParentedTree.fromstring('(S (NP (NP (PP x)) (NP (AP x)))'
                                       ' (VP (AP (NP (PP x)) (NP (AP x))))'
                                       ' (NP (RC (NP (AP x)))))')
        # This matches an NP that does not dominate a PP. Also, the NP
        # must either have a parent that is an NP or be dominated by a
        # VP:
        self.assertEqual(tgrep.tgrep_positions(tree,
                                               'NP !<< PP [> NP | >> VP]'),
                         [(0, 1), (1, 0, 1)])

        tree = ParentedTree.fromstring('(S (NP (AP (PP x) (VP x))) '
                                       '(NP (AP (PP x) (NP x))) (NP x))')
        # This matches an NP that dominates a PP which itself is
        # immediately followed by a VP. Note the use of parentheses to
        # group ". VP" with the PP rather than with the NP:
        self.assertEqual(tgrep.tgrep_positions(tree, 'NP << (PP . VP)'),
                         [(0,)])

        tree = ParentedTree.fromstring(
            '(S (NP (DET a) (NN cat) (PP (IN on) (NP x)))'
            ' (NP (DET a) (NN cat) (PP (IN on) (NP x)) (PP x))'
            ' (NP x))')
        # This matches an NP whose last child is a PP that begins with
        # the preposition "on":
        self.assertEqual(tgrep.tgrep_positions(tree,
                                               'NP <\' (PP <, (IN < on))'),
                         [(0,)])

        tree = ParentedTree.fromstring(
            '(S (S (C x) (A (B x))) (S (C x) (A x)) '
            '(S (D x) (A (B x))))')
        # The following pattern matches an S which has a child A and
        # another child that is a C and that the A has a child B:
        self.assertEqual(tgrep.tgrep_positions(tree, 'S < (A < B) < C'),
                         [(0,)])

        tree = ParentedTree.fromstring(
            '(S (S (A (B x) (C x))) (S (S (C x) (A (B x)))))')
        # However, this pattern means that S has child A and that A
        # has children B and C:
        self.assertEqual(tgrep.tgrep_positions(tree, 'S < ((A < B) < C)'),
                         [(0,)])

        # It is equivalent to this:
        self.assertEqual(tgrep.tgrep_positions(tree, 'S < (A < B < C)'),
                         [(0,)])

    def test_use_macros(self):
        '''
        Test defining and using tgrep2 macros.
        '''
        tree = ParentedTree.fromstring(
            '(VP (VB sold) (NP (DET the) '
            '(NN heiress)) (NP (NN deed) (PREP to) '
            '(NP (DET the) (NN school) (NN house))))')
        self.assertEqual(tgrep.tgrep_positions(
            tree, '@ NP /^NP/;\n@ NN /^NN/;\n@NP !< @NP !$.. @NN'),
                         [(1,), (2, 2)])
        # use undefined macro @CNP
        self.assertRaises(
            tgrep.TgrepException,
            tgrep.tgrep_positions,
            tree, '@ NP /^NP/;\n@ NN /^NN/;\n@CNP !< @NP !$.. @NN')

    def test_tokenize_node_labels(self):
        '''Test tokenization of labeled nodes.'''
        self.assertEqual(tgrep.tgrep_tokenize(
            'S < @SBJ < (@VP < (@VB $.. @OBJ))'),
                         ['S', '<', '@SBJ', '<', '(', '@VP', '<', '(',
                          '@VB', '$..', '@OBJ', ')', ')'])
        self.assertEqual(tgrep.tgrep_tokenize(
            'S < @SBJ=s < (@VP=v < (@VB $.. @OBJ))'),
                         ['S', '<', '@SBJ', '=', 's', '<', '(', '@VP',
                          '=', 'v', '<', '(', '@VB', '$..', '@OBJ', ')',
                          ')'])

    def test_tokenize_segmented_patterns(self):
        '''Test tokenization of segmented patterns.'''
        self.assertEqual(tgrep.tgrep_tokenize(
            'S < @SBJ=s < (@VP=v < (@VB $.. @OBJ)) : =s .. =v'),
                         ['S', '<', '@SBJ', '=', 's', '<', '(', '@VP',
                          '=', 'v', '<', '(', '@VB', '$..', '@OBJ', ')',
                          ')', ':', '=s', '..', '=v'])

    def test_labeled_nodes(self):
        '''
        Test labeled nodes.

        Test case from Emily M. Bender.
        '''
        search = '''
            # macros
            @ SBJ /SBJ/;
            @ VP /VP/;
            @ VB /VB/;
            @ VPoB /V[PB]/;
            @ OBJ /OBJ/;

            # 1 svo
            S < @SBJ=s < (@VP=v < (@VB $.. @OBJ)) : =s .. =v'''
        sent1 = ParentedTree.fromstring(
            '(S (NP-SBJ I) (VP (VB eat) (NP-OBJ (NNS apples))))')
        sent2 = ParentedTree.fromstring(
            '(S (VP (VB eat) (NP-OBJ (NNS apples))) (NP-SBJ I))')
        search_firsthalf = (search.split('\n\n')[0] +
                            'S < @SBJ < (@VP < (@VB $.. @OBJ))')
        search_rewrite = 'S < (/.*SBJ/ $.. (/VP/ < (/VB/ $.. /.*OBJ/)))'

        self.assertTrue(tgrep.tgrep_positions(sent1, search_firsthalf))
        self.assertTrue(tgrep.tgrep_positions(sent1, search))
        self.assertTrue(tgrep.tgrep_positions(sent1, search_rewrite))
        self.assertEqual(tgrep.tgrep_positions(sent1, search),
                         tgrep.tgrep_positions(sent1, search_rewrite))
        self.assertTrue(tgrep.tgrep_positions(sent2, search_firsthalf))
        self.assertFalse(tgrep.tgrep_positions(sent2, search))
        self.assertFalse(tgrep.tgrep_positions(sent2, search_rewrite))
        self.assertEqual(tgrep.tgrep_positions(sent2, search),
                         tgrep.tgrep_positions(sent2, search_rewrite))

    def test_multiple_conjs(self):
        '''
        Test that multiple (3 or more) conjunctions of node relations are
        handled properly.
        '''
        sent = ParentedTree.fromstring(
            '((A (B b) (C c)) (A (B b) (C c) (D d)))')
        # search = '(A < B < C < D)'
        # search_tworels = '(A < B < C)'
        self.assertEqual(tgrep.tgrep_positions(sent, '(A < B < C < D)'),
                         [(1,)])
        self.assertEqual(tgrep.tgrep_positions(sent, '(A < B < C)'),
                         [(0,), (1,)])

    def test_trailing_semicolon(self):
        '''
        Test that semicolons at the end of a tgrep2 search string won't
        cause a parse failure.
        '''
        tree = ParentedTree.fromstring(
            '(S (NP (DT the) (JJ big) (NN dog)) '
            '(VP bit) (NP (DT a) (NN cat)))')
        self.assertEqual(tgrep.tgrep_positions(tree, 'NN'),
                         [(0,2), (2,1)])
        self.assertEqual(tgrep.tgrep_positions(tree, 'NN;'),
                         [(0,2), (2,1)])
        self.assertEqual(tgrep.tgrep_positions(tree, 'NN;;'),
                         [(0,2), (2,1)])

if __name__ == '__main__':
    unittest.main()
