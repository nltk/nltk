# Natural Language Toolkit: Test Code for CFGs
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.cfg}.
"""

from nltk.cfg import *

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

# Make sure that type checking is turned on.
import nltk.chktype
nltk.chktype.type_safety_level(100)

class NonterminalTestCase(unittest.TestCase):
    "Test cases for L{nltk.cfg.Nonterminal}"
    def testEquality(self):
        "nltk.cfg.Nonterminal: test equality operators"
        S1 = Nonterminal('S')
        S2 = Nonterminal('S')
        VP1 = Nonterminal('VP')
        VP2 = Nonterminal('VP')
        vp = Nonterminal('vp')
        self.failUnlessEqual(S1, S1)
        self.failUnlessEqual(S1, S2)
        self.failUnlessEqual(S2, S1)
        self.failIfEqual(S1, VP1)
        self.failIfEqual(S1, VP2)
        self.failIfEqual(VP1, vp)

        # Explicityl test ==/!=
        self.failUnless(S1==S1)
        self.failUnless(S1==S2)
        self.failUnless(S2==S1)
        self.failIf(S1==VP1)
        self.failIf(S1==VP2)
        self.failIf(VP1==vp)
        self.failIf(S1!=S1)
        self.failIf(S1!=S2)
        self.failIf(S2!=S1)
        self.failUnless(S1!=VP1)
        self.failUnless(S1!=VP2)
        self.failUnless(VP1!=vp)

        # Explicitly test cmp
        self.failUnless(cmp(S1, S1) == 0)
        self.failUnless(cmp(S1, S2) == 0)
        self.failUnless(cmp(S2, S1) == 0)
        self.failIf(cmp(S1, VP1) == 0)
        self.failIf(cmp(S1, VP2) == 0)
        self.failIf(cmp(VP1, vp) == 0)

    def testSlash(self):
        "nltk.cfg.Nonterminal: test division operator"
        A = Nonterminal('A')
        B = Nonterminal('B')
        AslashB = Nonterminal('A/B')
        self.failUnless(A/B == AslashB)

    def testSymbol(self):
        "nltk.cfg.Nonterminal: test symbol()"
        for symbol in ['a', 'A', 'VP', 12, (1,2)]:
            self.failUnlessEqual(Nonterminal(symbol).symbol(), symbol)

    def testHash(self):
        "nltk.cfg.Nonterminal: test hash()"
        VP1 = Nonterminal('VP')
        VP2 = Nonterminal('VP')
        self.failUnlessEqual(hash(VP1), hash(VP2))

    def testRepr(self):
        "nltk.cfg.Nonterminal: test repr operator"
        self.failUnlessEqual(repr(Nonterminal('VP')), '<VP>')
        self.failUnlessEqual(repr(Nonterminal('vp')), '<vp>')
        self.failUnlessEqual(repr(Nonterminal(2)), '<2>')
        self.failUnlessEqual(repr(Nonterminal((1, 2))), '<(1, 2)>')

    def testStr(self):
        "nltk.cfg.Nonterminal: test str operator"
        self.failUnlessEqual(str(Nonterminal('VP')), 'VP')
        self.failUnlessEqual(str(Nonterminal('vp')), 'vp')
        self.failUnlessEqual(str(Nonterminal(2)), '2')
        self.failUnlessEqual(str(Nonterminal((1, 2))), '(1, 2)')

class CFGProductionTestCase(unittest.TestCase):
    "Test cases for L{nltk.cfg.CFGProduction}"
    def testLHS(self):
        "nltk.cfg.CFGProduction: test lhs()"
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [CFGProduction(A, B, C), CFGProduction(A2, *[C, B]),
             CFGProduction(A), CFGProduction(A, 'x', 'y', 'z'),
             CFGProduction(A, A, 'x')]
        for i in range(len(p)):
            self.failUnless(p[i].lhs() == A)
        self.failUnlessRaises(TypeError, CFGProduction, 'x')
        self.failUnlessRaises(TypeError, CFGProduction, 'x', A)
        self.failUnlessRaises(TypeError, CFGProduction, 'x', 'x')

    def testRHS(self):
        "nltk.cfg.CFGProduction: test rhs()"
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [CFGProduction(A, B, C), CFGProduction(A2, *[C, B, A]),
             CFGProduction(A), CFGProduction(A, 'x', 'y', 'z'),
             CFGProduction(A, A, 'x')]
        self.failUnless(p[0].rhs() == (B, C))
        self.failUnless(p[1].rhs() == (C, B, A))
        self.failUnless(p[2].rhs() == ())
        self.failUnless(p[3].rhs() == ('x', 'y', 'z'))
        self.failUnless(p[4].rhs() == (A2, 'x'))

    def testRepr(self):
        "nltk.cfg.CFGProduction: test repr operator"
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [CFGProduction(A, B, C), CFGProduction(A, *[C, B]),
             CFGProduction(A), CFGProduction(A, 'x', 'y', 'z'),
             CFGProduction(A, A, 'x')]
        self.failUnlessEqual(repr(p[0]), "[Production: A -> B C]")
        self.failUnlessEqual(repr(p[1]), "[Production: A -> C B]")
        self.failUnlessEqual(repr(p[2]), "[Production: A ->]")
        self.failUnlessEqual(repr(p[3]), "[Production: A -> 'x' 'y' 'z']")
        self.failUnlessEqual(repr(p[4]), "[Production: A -> A 'x']")

    def testStr(self):
        "nltk.cfg.CFGProduction: test str operator"
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [CFGProduction(A, B, C), CFGProduction(A, *[C, B]),
             CFGProduction(A), CFGProduction(A, 'x', 'y', 'z'),
             CFGProduction(A, A, 'x')]
        self.failUnlessEqual(str(p[0]), "A -> B C")
        self.failUnlessEqual(str(p[1]), "A -> C B")
        self.failUnlessEqual(str(p[2]), "A ->")
        self.failUnlessEqual(str(p[3]), "A -> 'x' 'y' 'z'")
        self.failUnlessEqual(str(p[4]), "A -> A 'x'")

    def testCompare(self):
        "nltk.cfg.CFGProduction: test comparison operators"
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        argslist = [(A,B,C), (A, C, 'x', B), (A,), (A, 'x', 'y')]
        for args1 in argslist:
            for args2 in argslist:
                if args1 == args2:
                    self.failUnlessEqual(CFGProduction(*args1),
                                         CFGProduction(*args2))
                    self.failUnless(CFGProduction(*args1) ==
                                    CFGProduction(*args2))
                    self.failUnless(cmp(CFGProduction(*args1),
                                        CFGProduction(*args2)) == 0)
                else:
                    self.failIfEqual(CFGProduction(*args1),
                                     CFGProduction(*args2))
                    self.failUnless(CFGProduction(*args1) !=
                                    CFGProduction(*args2))
                    self.failUnless(cmp(CFGProduction(*args1),
                                        CFGProduction(*args2)) != 0)

class CFGTestCase(unittest.TestCase):
    "Test cases for L{nltk.cfg.CFG}"
    def testCFG(self):
        "nltk.cfg.CFG: test constructor, productions() and start()"
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [CFGProduction(A, B, C), CFGProduction(A, *[C, B]),
             CFGProduction(A), CFGProduction(A, 'x', 'y', 'z'),
             CFGProduction(A, A, 'x')]
        cfg = CFG(A, p)
        self.failUnless(cfg.start() == A)
        self.failUnless(cfg.productions() == tuple(p))
        cfg = CFG(B, [])
        self.failUnless(cfg.start() == B)
        self.failUnless(cfg.productions() == ())
        cfg = CFG(B, ())
        self.failUnless(cfg.productions() == ())
        self.failUnlessRaises(TypeError, CFG, 0, [])
        self.failUnlessRaises(TypeError, CFG, A, [0])
        self.failUnlessRaises(TypeError, CFG, A, A)
        self.failUnlessRaises(TypeError, CFG, A, [A])

class PCFGTestCase(unittest.TestCase):
    "Test cases for L{nltk.cfg.PCFG}"
    def testCFG(self):
        "nltk.cfg.CFG: test constructor, productions() and start()"
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [PCFGProduction(0.5, A, B, C),
             PCFGProduction(0.2, A, *[C, B]),
             PCFGProduction(0.3, A),
             PCFGProduction(0.4, B, 'x', 'y', 'z'),
             PCFGProduction(0.6, B, B, 'x')]
        pcfg = PCFG(A, p)
        self.failUnless(pcfg.start() == A)
        self.failUnless(pcfg.productions() == tuple(p))
        pcfg = PCFG(B, [])
        self.failUnless(pcfg.start() == B)
        self.failUnless(pcfg.productions() == ())
        pcfg = PCFG(B, ())
        self.failUnless(pcfg.productions() == ())
        self.failUnlessRaises(TypeError, PCFG, 0, [])
        self.failUnlessRaises(TypeError, PCFG, A, [0])
        self.failUnlessRaises(TypeError, PCFG, A, A)
        self.failUnlessRaises(TypeError, PCFG, A, [A])
        p.append(PCFGProduction(0.1, B, B))
        self.failUnlessRaises(ValueError, PCFG, A, p)
        
def testsuite():
    t1 = unittest.makeSuite(NonterminalTestCase, 'test')
    t2 = unittest.makeSuite(CFGProductionTestCase, 'test')
    t3 = unittest.makeSuite(CFGTestCase, 'test')
    t4 = unittest.makeSuite(PCFGTestCase, 'test')
    return unittest.TestSuite( (t1, t2, t3, t4) )

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
