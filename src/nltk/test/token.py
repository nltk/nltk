# Natural Language Toolkit: Test Code for Tokens and Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk.token import *

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

class LocationTestCase(unittest.TestCase):
    """
    Unit test cases for C{token.Location}
    """
    def setUp(self):
        self.loc = Location(0, 10, source='foo.txt',
                            unit='c')

    def testStart(self):
        "nltk.token.Location: Start acessor test"
        self.failUnlessEqual(self.loc.start(), 0)

    def testEnd(self):
        "nltk.token.Location: End acessor test"
        self.failUnlessEqual(self.loc.end(), 10)

    def testSource(self):
        "nltk.token.Location: Source acessor test"
        self.failUnlessEqual(self.loc.source(), 'foo.txt')

    def testUnit(self):
        "nltk.token.Location: Unit acessor test"
        self.failUnlessEqual(self.loc.unit(), 'c')

    def testHash(self):
        "nltk.token.Location: Hash function test"
        loc2 = Location(0, 10, source='foo.txt',
                        unit='c')
        self.failUnlessEqual(hash(self.loc), hash(loc2))

    def testRepr(self):
        "nltk.token.Location: repr output tests"
        loc1 = Location(0, 1)
        loc2 = Location(0, 1, source='foo.txt')
        loc3 = Location(0, 1, unit='c')
        loc4 = Location(0, 1, source='foo.txt', unit='c')
        
        loc5 = Location(0, 10)
        loc6 = Location(0, 10, source='foo.txt')
        loc7 = Location(0, 10, unit='c')
        loc8 = Location(0, 10, source='foo.txt', unit='c')
        
        self.failUnlessEqual(repr(loc1), '@[0]')
        self.failUnlessEqual(repr(loc2), '@[0]')
        self.failUnlessEqual(repr(loc3), '@[0c]')
        self.failUnlessEqual(repr(loc4), '@[0c]')
        self.failUnlessEqual(repr(loc5), '@[0:10]')
        self.failUnlessEqual(repr(loc6), '@[0:10]')
        self.failUnlessEqual(repr(loc7), '@[0c:10c]')
        self.failUnlessEqual(repr(loc8), '@[0c:10c]')

    def testStr(self):
        "nltk.token.Location: str output tests"
        loc1 = Location(0, 1)
        loc2 = Location(0, 1, source='foo.txt')
        loc3 = Location(0, 1, unit='c')
        loc4 = Location(0, 1, source='foo.txt', unit='c')
        
        loc5 = Location(0, 10)
        loc6 = Location(0, 10, source='foo.txt')
        loc7 = Location(0, 10, unit='c')
        loc8 = Location(0, 10, source='foo.txt', unit='c')
        
        self.failUnlessEqual(str(loc1), "@[0]")
        self.failUnlessEqual(str(loc2), "@[0]@'foo.txt'")
        self.failUnlessEqual(str(loc3), "@[0c]")
        self.failUnlessEqual(str(loc4), "@[0c]@'foo.txt'")
        self.failUnlessEqual(str(loc5), "@[0:10]")
        self.failUnlessEqual(str(loc6), "@[0:10]@'foo.txt'")
        self.failUnlessEqual(str(loc7), "@[0c:10c]")
        self.failUnlessEqual(str(loc8), "@[0c:10c]@'foo.txt'")

    def testCmp(self):
        "nltk.token.Location: comparison tests (==, <, >)"
        # These use lexicographic order.
        loc1 = Location(0, 1)
        loc2 = Location(1, 3)
        loc3 = Location(2, 5)
        loc4 = Location(0, 1)
        loc5 = Location(2, 5)

        self.failUnless(loc1 == loc4)
        self.failUnless(loc3 == loc5)
        self.failUnless(loc1 < loc2)
        self.failUnless(loc2 > loc1)
        self.failUnless(loc1 < loc3)
        self.failUnless(loc3 > loc1)
        self.failUnless(loc2 < loc3)
        self.failUnless(loc3 > loc2)
        
        self.failIf(loc1 > loc2)
        self.failIf(loc2 < loc1)
        self.failIf(loc1 > loc3)
        self.failIf(loc3 < loc1)
        
        self.failIf(loc2 > loc3)
        self.failIf(loc3 < loc2)

    def testCmp2(self):
        "nltk.token.Location: comparison tests (prec, succ)"
        loc1 = Location(0, 1)
        loc2 = Location(1, 3)
        loc3 = Location(2, 5)
        loc4 = Location(0, 1)
        loc5 = Location(2, 5)

        self.failUnless(loc1.prec(loc2))
        self.failUnless(loc2.succ(loc1))
        self.failUnless(loc1.prec(loc3))
        self.failUnless(loc3.succ(loc1))
        
        self.failIf(loc1.succ(loc2))
        self.failIf(loc2.prec(loc1))
        self.failIf(loc1.succ(loc3))
        self.failIf(loc3.prec(loc1))
        
        self.failIf(loc2.prec(loc3))
        self.failIf(loc2.succ(loc3))
        self.failIf(loc3.prec(loc2))
        self.failIf(loc3.succ(loc2))

    def testCmpExecptions(self):
        "nltk.token.Location: comparison exception tests (<=, >=, cmp)"
        loc1 = Location(0, 15)
        loc2 = Location(0, 15, source='foo.txt')
        loc3 = Location(0, 15, unit='c')
        loc4 = Location(0, 15, unit='c', source='foo.txt')
        loc5 = Location(10, 20)

        def t1(l1=loc1, l2=loc2): l1==l2
        def t2(l1=loc1, l3=loc3): l1==l3
        def t3(l1=loc1, l4=loc4): l1==l4
        def t4(l2=loc2, l3=loc3): l2==l3
        def t5(l2=loc2, l4=loc4): l2==l4
        def t6(l3=loc3, l4=loc4): l3==l4
        
        self.failUnlessRaises(ValueError, t1)
        self.failUnlessRaises(ValueError, t2)
        self.failUnlessRaises(ValueError, t3)
        self.failUnlessRaises(ValueError, t4)
        self.failUnlessRaises(ValueError, t5)
        self.failUnlessRaises(ValueError, t6)

        def t1(l1=loc1, l2=loc2): l1<l2
        def t2(l1=loc1, l3=loc3): l1>l3
        def t3(l1=loc1, l4=loc4): l1<=l4
        def t4(l2=loc2, l3=loc3): l2>=l3
        def t5(l2=loc2, l4=loc4): l2.prec(l4)
        def t6(l3=loc3, l4=loc4): l3.succ(l4)
        
        self.failUnlessRaises(ValueError, t1)
        self.failUnlessRaises(ValueError, t2)
        self.failUnlessRaises(ValueError, t3)
        self.failUnlessRaises(ValueError, t4)
        self.failUnlessRaises(ValueError, t5)
        self.failUnlessRaises(ValueError, t6)


class TokenTestCase(unittest.TestCase):
    """
    Unit test cases for C{token.Token}
    """
    def setUp(self):
        self.loc = Location(0, 10)
        self.type = "dog"
        self.token = Token(self.type, self.loc)

    def testType(self):
        "nltk.token.Token: type accessor test"
        self.failUnlessEqual(self.token.type(), self.type)

    def testLocation(self):
        "nltk.token.Token: location accessor test"
        self.failUnless(self.token.loc() == self.loc)
        
    def testHash(self):
        "nltk.token.Token: hash function test"
        token2 = Token('dog', 0, 10)
        self.failUnlessEqual(hash(self.token), hash(token2))
        
    def testRepr(self):
        "nltk.token.Token: repr output tests"
        t1=Token('dog')
        t2=Token('dog', 0, 5)
        t3=Token('dog', 0, 5, unit='c', source='foo.txt')

        self.failUnlessEqual(repr(t1), "'dog'@[?]")
        self.failUnlessEqual(repr(t2), "'dog'@[0:5]")
        self.failUnlessEqual(repr(t3), "'dog'@[0c:5c]")
        
    def testStr(self):
        "nltk.token.Token: str output tests"
        t1=Token('dog')
        t2=Token('dog', 0, 5)
        t3=Token('dog', 0, 5, unit='c', source='foo.txt')

        self.failUnlessEqual(str(t1), "'dog'@[?]")
        self.failUnlessEqual(str(t2), "'dog'@[0:5]")
        self.failUnlessEqual(str(t3), "'dog'@[0c:5c]@'foo.txt'")

    def testCmp(self):
        "nltk.token.Token: comparison tests (==, !=, <, >, <=, >=)"
        self.failIf(Token('dog', None) == Token('dog', None))
        self.failUnless(Token('dog', None) != Token('dog', None))
        self.failUnless(Token('dog', None) != Token('dog', 1))
        self.failUnless(Token('dog', 1) != Token('dog', None))

        self.failUnless(Token('dog', 1) == Token('dog', 1))
        self.failUnless(Token('dog', 1,7) == Token('dog', 1,7))

        def t1(): Token('dog', 1, unit='c') == Token('dog', 1, unit='s')
        def t2(): (Token('dog', 1, source='foo.txt') ==
                   Token('dog', 1, source='bar.txt'))
        self.failUnlessRaises(ValueError, t1)
        self.failUnlessRaises(ValueError, t2)

        t1=Token('dog')
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1<t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1>t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1<=t1)
        self.failUnlessRaises(AssertionError, lambda t1=t1: t1>=t1)

    def testConstructor(self):
        "nltk.token.Token: constructor tests"
        t1=Token('dog')
        t2=Token('dog', 0)
        t3=Token('dog', 0, 5)
        t4=Token('dog', 0, 5, unit='c', source='foo.txt')
        t5=Token('dog', Location(0, 5))

        self.failUnlessEqual(t1.type(), 'dog')
        self.failUnlessEqual(t2.type(), 'dog')
        self.failUnlessEqual(t3.type(), 'dog')
        self.failUnlessEqual(t4.type(), 'dog')
        self.failUnlessEqual(t5.type(), 'dog')
        self.failUnless(t1.loc() == None)
        self.failUnless(t2.loc() == Location(0))
        self.failUnless(t3.loc() == Location(0,5))
        self.failUnless(t4.loc() ==
                        Location(0, 5, unit='c', source='foo.txt'))
        self.failUnless(t5.loc() == Location(0, 5))

        self.failUnlessRaises(TypeError, Token, 'dog',
                              Location(0), 5)
        self.failUnlessRaises(TypeError, Token, 'dog',
                              Location(0), unit='c')
        self.failUnlessRaises(TypeError, Token, 'dog',
                              None, 5)
        self.failUnlessRaises(TypeError, Token, 'dog',
                              None, unit='c')
            
class WSTokenizerTestCase(unittest.TestCase):
    """
    Unit test cases for C{token.WSTokenizer}
    """
    def setUp(self):
        self.tokenizer = WSTokenizer()

    def testTokenize(self):
        "nltk.token.WSTokenizer: tokenize method tests"
        ts1 = self.tokenizer.tokenize("this is a test")
        ts2 = [Token('this', 0, unit='w'), Token('is', 1, unit='w'),
               Token('a', 2, unit='w'), Token('test', 3, unit='w')]
        self.failUnlessEqual(ts1, ts2)

        ts1 = self.tokenizer.tokenize("this is a test", source='foo.txt')
        ts2 = [Token('this', 0, unit='w', source='foo.txt'),
               Token('is', 1, unit='w', source='foo.txt'),
               Token('a', 2, unit='w', source='foo.txt'),
               Token('test', 3, unit='w', source='foo.txt')]
        self.failUnlessEqual(ts1, ts2)
    
        ts1 = self.tokenizer.tokenize("   this  is a   test ")
        ts2 = [Token('this', 0, unit='w'), Token('is', 1, unit='w'),
               Token('a', 2, unit='w'), Token('test', 3, unit='w')]
        self.failUnlessEqual(ts1, ts2)

def testsuite():
    """
    Return a PyUnit testsuite for the token module.
    """
    
    tests = unittest.TestSuite()

    loctests = unittest.makeSuite(LocationTestCase, 'test')
    tests = unittest.TestSuite( (tests, loctests) )

    toktests = unittest.makeSuite(TokenTestCase, 'test')
    tests = unittest.TestSuite( (tests, toktests) )

    tokenizertests = unittest.makeSuite(WSTokenizerTestCase, 'test')
    tests = unittest.TestSuite( (tests, tokenizertests) )

    return tests

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
