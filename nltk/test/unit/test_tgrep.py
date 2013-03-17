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

if __name__ == '__main__' and sys.argv != ['']:
    unittest.main()
