# Natural Language Toolkit: Test Code for Trees
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.tree}.

@todo: Test L{nltk.tree.ProbabilisticTreeToken}
@todo: Test L{nltk.tree.parse_treebank}
@todo: Test L{nltk.tree.TreebankTokenizer}
"""

from nltk.tree import *
from nltk.token import WSTokenizer

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

class TreeTestCase(unittest.TestCase):
    """
    Unit test cases for C{tree.Tree}
    """
    def setUp(self):
        self.dp1 = Tree('dp', Tree('d', 'the'), Tree('np', 'dog'))
        self.dp2 = Tree('dp', Tree('d', 'the'), Tree('np', 'cat'))
        self.vp = Tree('vp', Tree('v', 'chased'), self.dp2)
        self.tree = Tree('s', self.dp1, self.vp)

    def testConstructor(self):
        "nltk.tree.Tree: constructor tests"
        # We can mix nodes and leaves on one level.
        self.failUnlessEqual(Tree(1, 2, Tree(3), 4, Tree(5, 6)),
                             Tree(1, 2, Tree(3), 4, Tree(5, 6)))

    def testNode(self):
        "nltk.tree.Tree: node accessor tests"
        self.failUnlessEqual(self.tree.node(), 's')
        self.failUnlessEqual(self.tree[0].node(), 'dp')
        self.failUnlessEqual(self.tree[1][0].node(), 'v')

    def testGetItem(self):
        "nltk.tree.Tree: [] operator tests"
        self.failUnlessEqual(self.tree[0], self.dp1)
        self.failUnlessEqual(self.tree[1], self.vp)
        self.failUnlessEqual(self.tree[1][1], self.dp2)

    def testLen(self):
        "nltk.tree.Tree: len operator tests"
        self.failUnlessEqual(len(self.tree), 2)
        self.failUnlessEqual(len(self.dp1), 2)
        self.failUnlessEqual(len(self.dp1[0]), 1)
        self.failUnlessEqual(len(Tree('n')), 0)
        self.failUnlessEqual(len(Tree('n', 'c')), 1)

    def testRepr(self):
        "nltk.tree.Tree: repr output tests"
        self.failUnlessEqual(repr(self.vp), "('vp': ('v': 'chased') " + 
                             "('dp': ('d': 'the') ('np': 'cat')))")
        self.failUnlessEqual(repr(self.dp1), "('dp': ('d': 'the') "+
                             "('np': 'dog'))")
        self.failUnlessEqual(repr(Tree('n')), "('n':)")
        self.failUnlessEqual(repr(Tree('n', 'c')), "('n': 'c')")
        self.failUnlessEqual(repr(Tree(1, 2)), "(1: 2)")
        self.failUnlessEqual(repr(Tree( (1,2), (3,4) )), "((1, 2): (3, 4))")
        
    def testStr(self):
        "nltk.tree.Tree: str output tests"
        self.failUnlessEqual(str(self.vp), "('vp': ('v': 'chased') " + 
                             "('dp': ('d': 'the') ('np': 'cat')))")
        self.failUnlessEqual(str(self.dp1), "('dp': ('d': 'the') "+
                             "('np': 'dog'))")
        self.failUnlessEqual(str(Tree('n')), "('n':)")
        self.failUnlessEqual(str(Tree('n', 'c')), "('n': 'c')")
        self.failUnlessEqual(str(Tree(1, 2)), "(1: 2)")
        self.failUnlessEqual(str(Tree( (1,2), (3,4) )), "((1, 2): (3, 4))")

    def testLeaves(self):
        "nltk.tree.Tree: leaves method tests"
        self.failUnlessEqual(self.dp1.leaves(), ("the", "dog"))
        self.failUnlessEqual(self.tree.leaves(),
                             ("the", "dog", "chased", "the", "cat"))
        self.failUnlessEqual(self.vp[0].leaves(), ("chased",))
        self.failUnlessEqual(Tree('n').leaves(), ())

    def testNodes(self):
        "nltk.tree.Tree: nodes method tests"
        self.failUnlessEqual(self.dp1.nodes(),
                             Tree('dp', Tree('d'), Tree('np')))
        tnodes = Tree('s', Tree('dp', Tree('d'), Tree('np')),
                      Tree('vp', Tree('v'),
                           Tree('dp', Tree('d'), Tree('np'))))
        self.failUnlessEqual(self.tree.nodes(), tnodes)
        self.failUnlessEqual(self.vp[0].nodes(), Tree('v'))
        self.failUnlessEqual(Tree('n'), Tree('n'))

    def testCmp(self):
        "nltk.tree.Tree: comparison tests"
        self.failUnlessEqual(Tree(1,2), Tree(1,2))
        self.failUnlessEqual(Tree(1,Tree(2,3), Tree(4,5)),
                        Tree(1,Tree(2,3), Tree(4,5)))
        self.failUnlessEqual(Tree(1), Tree(1))
        self.failUnlessEqual(self.tree, self.tree)
        self.failUnlessEqual(self.dp1, self.dp1)

        # Explicitly test ==/!=
        self.failIf(Tree(1,2) != Tree(1,2))
        self.failUnless(Tree(1,2) == Tree(1,2))
        self.failIf(Tree(1,Tree(2,3), Tree(4,5)) !=
                    Tree(1,Tree(2,3), Tree(4,5)))
        self.failUnless(Tree(1,Tree(2,3), Tree(4,5)) ==
                        Tree(1,Tree(2,3), Tree(4,5)))
        self.failIf(Tree(1) != Tree(1))
        self.failUnless(Tree(1) == Tree(1))
        self.failIf(self.tree != self.tree)
        self.failUnless(self.tree == self.tree)
        self.failIf(self.dp1 != self.dp1)
        self.failUnless(self.dp1 == self.dp1)

        # Explicitly test cmp.  Right now, these raise exceptions, but
        # that's not really safe; it should be changed.
        #self.failIf(cmp(Tree(1,2), Tree(1,2)) != 0)
        #self.failUnless(cmp(Tree(1,2), Tree(1,2)) != 0)
        #self.failIf(cmp(Tree(1,Tree(2,3), Tree(4,5)),
        #                Tree(1,Tree(2,3), Tree(4,5))) != 0)
        #self.failUnless(cmp(Tree(1,Tree(2,3), Tree(4,5)),
        #                    Tree(1,Tree(2,3), Tree(4,5))) != 0)
        #self.failIf(cmp(Tree(1), Tree(1)) != 0)
        #self.failUnless(cmp(Tree(1), Tree(1)) != 0)
        #self.failIf(cmp(self.tree, self.tree) != 0)
        #self.failUnless(cmp(self.tree, self.tree) != 0)
        #self.failIf(cmp(self.dp1, self.dp1) != 0)
        #self.failUnless(cmp(self.dp1, self.dp1) != 0)
        
        t1=Tree('np', 'dog')
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1<t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1>t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1<=t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1>=t1)

    def testHeight(self):
        "nltk.tree.Tree: height method tests"
        self.failUnlessEqual(self.tree.height(), 5)
        self.failUnlessEqual(self.vp.height(), 4)
        self.failUnlessEqual(self.dp1.height(), 3)
        self.failUnlessEqual(self.dp1[0].height(), 2)
        self.failUnlessEqual(Tree('node').height(), 1)

class TreeTokenTestCase(unittest.TestCase):
    """
    Unit test cases for C{tree.TreeToken}
    """
    def setUp(self):
        text = 'the dog chased the cat'
        self.words = WSTokenizer().tokenize(text)
        self.dp1 = TreeToken('dp', TreeToken('d', self.words[0]),
                             TreeToken('np', self.words[1]))
        self.dp2 = TreeToken('dp', TreeToken('d', self.words[3]),
                        TreeToken('np', self.words[4]))
        self.vp = TreeToken('vp', TreeToken('v', self.words[2]), self.dp2)
        self.tree = TreeToken('s', self.dp1, self.vp)

    def testConstructor(self):
        "nltk.tree.Tree: constructor tests"
        # We can mix nodes and leaves on one level.
        TreeToken(1, Token(2), TreeToken(3),
                  Token(4), TreeToken(5, Token(6)))

        def token(type,start): return Token(type, Location(start))
        # Locations must be properly ordered.
        self.failUnlessRaises(ValueError, lambda :
                              TreeToken('n', TreeToken('n', token(1,5)),
                                        token(1,1),
                                        TreeToken('n', token(1,2)),
                                        token(1,3)))
        self.failUnlessRaises(ValueError, lambda :
                              TreeToken('n', TreeToken('n', token(1,0)),
                                        token(1,1),
                                        TreeToken('n', token(1,2)),
                                        token(1,0)))
        self.failUnlessRaises(ValueError, lambda :
                              TreeToken('n', TreeToken('n', token(1,0)),
                                        token(1,5),
                                        TreeToken('n', token(1,3)),
                                        token(1,7)))
        self.failUnlessRaises(ValueError, lambda :
                              TreeToken('n', TreeToken('n', token(1,0)),
                                        token(1,5),
                                        TreeToken('n', Token(1,None)),
                                        token(1,3)))
                                         
                                         
        
    def testNode(self):
        "nltk.tree.TreeToken: node accessor tests"
        self.failUnlessEqual(self.tree.node(), 's')
        self.failUnlessEqual(self.tree[0].node(), 'dp')
        self.failUnlessEqual(self.tree[1][0].node(), 'v')

    def testGetItem(self):
        "nltk.tree.TreeToken: [] operator tests"
        self.failUnless(self.tree[0] == self.dp1)
        self.failUnless(self.tree[1] == self.vp)
        self.failUnless(self.tree[1][1] == self.dp2)

    def testLen(self):
        "nltk.tree.TreeToken: len operator tests"
        self.failUnlessEqual(len(self.tree), 2)
        self.failUnlessEqual(len(self.dp1), 2)
        self.failUnlessEqual(len(self.dp1[0]), 1)
        self.failUnlessEqual(len(TreeToken('n')), 0)
        self.failUnlessEqual(len(TreeToken('n', Token('c'))), 1)

    def testRepr(self):
        "nltk.tree.TreeToken: repr output tests"
        self.failUnlessEqual(repr(self.vp), "('vp': ('v': 'chased') " + 
                             "('dp': ('d': 'the') ('np': 'cat')))@[2w:5w]")
        self.failUnlessEqual(repr(self.dp1),
                             "('dp': ('d': 'the') ('np': 'dog'))@[0w:2w]")
        self.failUnlessEqual(repr(TreeToken('n')), "('n':)@[?]")
        self.failUnlessEqual(repr(TreeToken('n', Token('c'))),
                             "('n': 'c')@[?]")
        self.failUnlessEqual(repr(TreeToken(1, Token(2))), "(1: 2)@[?]")
        
    def testStr(self):
        "nltk.tree.TreeToken: str output tests"
        self.failUnlessEqual(repr(self.vp), "('vp': ('v': 'chased') " + 
                             "('dp': ('d': 'the') ('np': 'cat')))@[2w:5w]")
        self.failUnlessEqual(repr(self.dp1), "('dp': ('d': 'the') "+
                             "('np': 'dog'))@[0w:2w]")
        self.failUnlessEqual(repr(TreeToken('n')), "('n':)@[?]")
        self.failUnlessEqual(repr(TreeToken('n', Token('c'))), "('n': 'c')@[?]")
        self.failUnlessEqual(repr(TreeToken(1, Token(2))), "(1: 2)@[?]")

    def testLeaves(self):
        "nltk.tree.TreeToken: leaves method tests"
        self.failUnless(self.dp1.leaves() == (self.words[0], self.words[1]))
        self.failUnless(self.tree.leaves() == tuple(self.words))
        self.failUnless(self.vp[0].leaves() == (self.words[2],))
        self.failUnless(TreeToken('n').leaves() == ())

    def testNodes(self):
        "nltk.tree.TreeToken: nodes method tests"
        self.failUnless(self.dp1.nodes() == TreeToken('dp', TreeToken('d'), TreeToken('np')))
        tnodes = TreeToken('s', TreeToken('dp', TreeToken('d'), TreeToken('np')),
                      TreeToken('vp', TreeToken('v'),
                           TreeToken('dp', TreeToken('d'), TreeToken('np'))))
        self.failUnless(self.tree.nodes() == tnodes)
        self.failUnless(self.vp[0].nodes() == TreeToken('v'))
        self.failUnless(TreeToken('n') == TreeToken('n'))

    def testCmp(self):
        "nltk.tree.TreeToken: comparison tests"
        def token(type,start): return Token(type, Location(start))
        self.failIf(TreeToken(1,token(2,0)) != TreeToken(1,token(2,0)))
        self.failUnless(TreeToken(1,token(2,0)) == TreeToken(1,token(2,0)))
        self.failIf(TreeToken(1,TreeToken(2,token(3,0)),
                              TreeToken(4,token(5,1))) !=
                    TreeToken(1,TreeToken(2,token(3,0)),
                              TreeToken(4,token(5,1))))
        self.failUnless(TreeToken(1,TreeToken(2,token(3,0)),
                                  TreeToken(4,token(5,1))) ==
                        TreeToken(1,TreeToken(2,token(3,0)),
                                  TreeToken(4,token(5,1))))
        self.failIf(TreeToken(1) != TreeToken(1))
        self.failUnless(TreeToken(1) == TreeToken(1))
        self.failIf(self.tree != self.tree)
        self.failUnless(self.tree == self.tree)
        self.failIf(self.dp1 != self.dp1)
        self.failUnless(self.dp1 == self.dp1)
        
        t1=TreeToken('np', Token('dog'))
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1<t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1>t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1<=t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1>=t1)

    def testHeight(self):
        "nltk.tree.TreeToken: height method tests"
        self.failUnlessEqual(self.tree.height(), 5)
        self.failUnlessEqual(self.vp.height(), 4)
        self.failUnlessEqual(self.dp1.height(), 3)
        self.failUnlessEqual(self.dp1[0].height(), 2)
        self.failUnlessEqual(TreeToken('node').height(), 1)

def testsuite():
    """
    Return a PyUnit testsuite for the tree module.
    """
    
    tests = unittest.TestSuite()

    treetests = unittest.makeSuite(TreeTestCase, 'test')
    tests = unittest.TestSuite( (tests, treetests) )

    treetokentests = unittest.makeSuite(TreeTokenTestCase, 'test')
    tests = unittest.TestSuite( (tests, treetokentests) )

    return tests

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
