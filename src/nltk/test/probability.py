# Natural Language Toolkit: Test Code for Probability and Statistics
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$


from nltk.probability import *

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

class SampleEventTestCase(unittest.TestCase):
    """
    Unit test cases for C{probability.SampleEvent}
    """
    def testConstructor(self):
        "nltk.probability.SampleEvent: constructor tests"
        x = SampleEvent(1)
        y = SampleEvent('a')
        z = SampleEvent( (1,2,3, (4,5)) )

    def testContains(self):
        "nltk.probability.SampleEvent: containership tests"
        x = SampleEvent(1)
        y = SampleEvent('a')
        z = SampleEvent( (1,2,3, (4,5)) )

        self.failUnless(1 in x)
        self.failUnless('a' in y)
        self.failUnless( (1,2,3, (4,5)) in z)

        self.failIf(0 in x)
        self.failIf(0 in x)
        self.failIf('A' in y)
        self.failIf('z' in y)
        self.failIf('a' in z)
        self.failIf(1 in z)

        self.failUnless(x.contains(1))
        self.failUnless(y.contains('a'))
        self.failUnless(z.contains( (1,2,3, (4,5)) ))

        self.failIf(x.contains(0))
        self.failIf(x.contains(0))
        self.failIf(y.contains('A'))
        self.failIf(y.contains('z'))
        self.failIf(z.contains('a'))
        self.failIf(z.contains(1))

    def testEquals(self):
        "nltk.probability.SampleEvent: equality tests"
        x = SampleEvent(1)
        y = SampleEvent('a')
        a = SampleEvent('a')
        b = SampleEvent(0)

        self.failIf(x == y)
        self.failIf(x == a)
        self.failIf(x == b)
        self.failIf(y == x)

        self.failUnless(y == a)
        self.failUnless(a == y)
        
        self.failIf(y == b)
        self.failIf(a == x)
        self.failIf(a == b)
        self.failIf(b == x)
        self.failIf(b == y)
        self.failIf(b == a)

        self.failIf(y != a)
        self.failIf(a != y)
        
        self.failUnless(y != b)
        self.failUnless(a != x)
        self.failUnless(a != b)
        self.failUnless(b != x)
        self.failUnless(b != y)
        self.failUnless(b != a)


def testsuite():
    """
    Return a PyUnit testsuite for the probability module.
    """
    
    tests = unittest.TestSuite()

    eventtests = unittest.makeSuite(SampleEventTestCase, 'test')
    tests = unittest.TestSuite( (tests, eventtests) )

    return tests

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()

