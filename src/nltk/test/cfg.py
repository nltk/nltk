# Natural Language Toolkit: Test Code for CFGs
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk.cfg import *

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

# Make sure that type checking is turned on.
import nltk.chktype
nltk.chktype.type_safety_level(100)

class NonterminalTestCase(unittest.TestCase):
    def testEquality(self):
        S1 = Nonterminal('S')
        S2 = Nonterminal('S')
        VP1 = Nonterminal('VP')
        VP2 = Nonterminal('VP')
        self.failUnless(S1==S1)
        self.failUnless(S1==S2)
        self.failUnless(S2==S1)
        self.failIf(S1==VP1)
        self.failIf(S1==VP2)
        self.failIf(S1!=S1)
        self.failIf(S1!=S2)
        self.failIf(S2!=S1)
        self.failUnless(S1!=VP1)
        self.failUnless(S1!=VP2)

    def testSlash(self):
        A = Nonterminal('A')
        B = Nonterminal('B')
        AslashB = Nonterminal('A/B')
        self.failUnless(A/B == AslashB)

class CFGProductionTestCase(unittest.TestCase):
    def testLHS(self):
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [CFGProduction(A, B, C), CFGProduction(A, *[C, B]),
             CFGProduction(A), CFGProduction(A, 'x', 'y', 'z'),
             CFGProduction(A, A, 'x')]
        for i in range(len(p)):
            self.failUnless(p[i].lhs() == A)
        self.failUnlessRaises(TypeError, lambda: CFGProduction('x'))
        self.failUnlessRaises(TypeError, lambda: CFGProduction('x', A))
        self.failUnlessRaises(TypeError, lambda: CFGProduction('x', 'x'))

    def testRHS(self):
        A, A2, B, C = [Nonterminal(s) for s in 'A A B C'.split()]
        p = [CFGProduction(A, B, C), CFGProduction(A, *[C, B]),
             CFGProduction(A), CFGProduction(A, 'x', 'y', 'z'),
             CFGProduction(A, A, 'x')]
        self.failUnless(p[0].rhs() == (B, C))
        self.failUnless(p[2].rhs() == ())
        self.failUnless(p[3].rhs() == ('x', 'y', 'z'))
        self.failUnless(p[4].rhs() == (A2, 'x'))

class CFGTestCase(unittest.TestCase):
    def testCFG(self):
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
        self.failUnlessRaises(TypeError, lambda: CFG(0, []))
        self.failUnlessRaises(TypeError, lambda: CFG(A, [0]))
        self.failUnlessRaises(TypeError, lambda: CFG(A, A))
        self.failUnlessRaises(TypeError, lambda: CFG(A, [A]))

class PCFGTestCase(unittest.TestCase):
    def testCFG(self):
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
        self.failUnlessRaises(TypeError, lambda: PCFG(0, []))
        self.failUnlessRaises(TypeError, lambda: PCFG(A, [0]))
        self.failUnlessRaises(TypeError, lambda: PCFG(A, A))
        self.failUnlessRaises(TypeError, lambda: PCFG(A, [A]))
        p.append(PCFGProduction(0.1, B, B))
        self.failUnlessRaises(ValueError, lambda: PCFG(A, p))
        
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
