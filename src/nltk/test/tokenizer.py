# Natural Language Toolkit: Test Code for Tokens and Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.tokenizer}.

@todo: Test L{nltk.token.CharTokenizer}
@todo: Test L{nltk.token.LineTokenizer}
"""

from nltk.token import *
from nltk.tokenizer import *

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

class WSTokenizerTestCase(unittest.TestCase):
    """
    Unit test cases for L{nltk.token.WSTokenizer}
    """
    def setUp(self):
        self.tokenizer = WSTokenizer()

    def testTokenize(self):
        "nltk.token.WSTokenizer: tokenize method tests"
        ts1 = self.tokenizer.tokenize("this is a test")
        ts2 = [Token('this', Location(0, unit='w')),
               Token('is', Location(1, unit='w')),
               Token('a', Location(2, unit='w')),
               Token('test', Location(3, unit='w'))]
        self.failUnlessEqual(ts1, ts2)

        ts1 = self.tokenizer.tokenize("this is a test", source='foo.txt')
        ts2 = [Token('this', Location(0, unit='w', source='foo.txt')),
               Token('is', Location(1, unit='w', source='foo.txt')),
               Token('a', Location(2, unit='w', source='foo.txt')),
               Token('test', Location(3, unit='w', source='foo.txt'))]
        self.failUnlessEqual(ts1, ts2)
    
        ts1 = self.tokenizer.tokenize("   this  is a   test ")
        ts2 = [Token('this', Location(0, unit='w', source='foo.txt')),
               Token('is', Location(1, unit='w', source='foo.txt')),
               Token('a', Location(2, unit='w', source='foo.txt')),
               Token('test', Location(3, unit='w', source='foo.txt'))]
        self.failUnlessEqual(ts1, ts2)

class WSTokenizerTestCase(unittest.TestCase):
    """
    Unit test cases for L{nltk.token.WSTokenizer}
    """
    def setUp(self):
        self.tokenizer = WSTokenizer()

    def testTokenize(self):
        "nltk.token.WSTokenizer: tokenize method tests"
        ts1 = self.tokenizer.tokenize("this is a test")
        ts2 = [Token('this', Location(0, unit='w')),
               Token('is', Location(1, unit='w')),
               Token('a', Location(2, unit='w')),
               Token('test', Location(3, unit='w'))]
        self.failUnlessEqual(ts1, ts2)

        ts1 = self.tokenizer.tokenize("this is a test", source='foo.txt')
        ts2 = [Token('this', Location(0, unit='w', source='foo.txt')),
               Token('is', Location(1, unit='w', source='foo.txt')),
               Token('a', Location(2, unit='w', source='foo.txt')),
               Token('test', Location(3, unit='w', source='foo.txt'))]
        self.failUnlessEqual(ts1, ts2)
    
        ts1 = self.tokenizer.tokenize("   this  is a   test ")
        ts2 = [Token('this', Location(0, unit='w')),
               Token('is', Location(1, unit='w')),
               Token('a', Location(2, unit='w')),
               Token('test', Location(3, unit='w'))]
        self.failUnlessEqual(ts1, ts2)

    def testXTokenize(self):
        "nltk.token.WSTokenizer: xtokenize method tests"
        ts1 = self.tokenizer.xtokenize("this is a test")
        ts2 = [Token('this', Location(0, unit='w')),
               Token('is', Location(1, unit='w')),
               Token('a', Location(2, unit='w')),
               Token('test', Location(3, unit='w'))]
        self.failUnlessEqual(list(ts1), ts2)

        ts1 = self.tokenizer.xtokenize("this is a test", source='foo.txt')
        ts2 = [Token('this', Location(0, unit='w', source='foo.txt')),
               Token('is', Location(1, unit='w', source='foo.txt')),
               Token('a', Location(2, unit='w', source='foo.txt')),
               Token('test', Location(3, unit='w', source='foo.txt'))]
        self.failUnlessEqual(list(ts1), ts2)
    
        ts1 = self.tokenizer.xtokenize("   this  is a   test ")
        ts2 = [Token('this', Location(0, unit='w')),
               Token('is', Location(1, unit='w')),
               Token('a', Location(2, unit='w')),
               Token('test', Location(3, unit='w'))]
        self.failUnlessEqual(list(ts1), ts2)

class RETokenizerTestCase(unittest.TestCase):
    """
    Unit test cases for L{nltk.token.WSTokenizer}
    """
    def setUp(self):
        self.tokenizers = [RETokenizer('\s+', negative=1),
                           RETokenizer('\w+')]

    def testTokenize(self):
        "nltk.token.RETokenizer: tokenize method tests"
        for tokenizer in self.tokenizers:
            ts1 = tokenizer.tokenize("this is a test")
            ts2 = [Token('this', Location(0, unit='w')),
                   Token('is', Location(1, unit='w')),
                   Token('a', Location(2, unit='w')),
                   Token('test', Location(3, unit='w'))]
            self.failUnlessEqual(ts1, ts2)
    
            ts1 = tokenizer.tokenize("this is a test", source='foo.txt')
            ts2 = [Token('this', Location(0, unit='w', source='foo.txt')),
                   Token('is', Location(1, unit='w', source='foo.txt')),
                   Token('a', Location(2, unit='w', source='foo.txt')),
                   Token('test', Location(3, unit='w', source='foo.txt'))]
            self.failUnlessEqual(ts1, ts2)
        
            ts1 = tokenizer.tokenize("   this  is a   test ")
            ts2 = [Token('this', Location(0, unit='w')),
                   Token('is', Location(1, unit='w')),
                   Token('a', Location(2, unit='w')),
                   Token('test', Location(3, unit='w'))]
            self.failUnlessEqual(ts1, ts2)
    
    def testXtokenize(self):
        "nltk.token.RETokenizer: xtokenize method tests"
        for tokenizer in self.tokenizers:
            ts1 = tokenizer.xtokenize("this is a test")
            ts2 = [Token('this', Location(0, unit='w')),
                   Token('is', Location(1, unit='w')),
                   Token('a', Location(2, unit='w')),
                   Token('test', Location(3, unit='w'))]
            self.failUnlessEqual(list(ts1), ts2)
    
            ts1 = tokenizer.xtokenize("this is a test", source='foo.txt')
            ts2 = [Token('this', Location(0, unit='w', source='foo.txt')),
                   Token('is', Location(1, unit='w', source='foo.txt')),
                   Token('a', Location(2, unit='w', source='foo.txt')),
                   Token('test', Location(3, unit='w', source='foo.txt'))]
            self.failUnlessEqual(list(ts1), ts2)
        
            ts1 = tokenizer.xtokenize("   this  is a   test ")
            ts2 = [Token('this', Location(0, unit='w')),
                   Token('is', Location(1, unit='w')),
                   Token('a', Location(2, unit='w')),
                   Token('test', Location(3, unit='w'))]
            self.failUnlessEqual(list(ts1), ts2)
    
def testsuite():
    """
    Return a PyUnit testsuite for the token module.
    """
    t1 = unittest.makeSuite(WSTokenizerTestCase, 'test')
    t2 = unittest.makeSuite(RETokenizerTestCase, 'test')
    return unittest.TestSuite( (t1, t2) )

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
