# Natural Language Toolkit: Test Code for Probability and Statistics
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$


from nltk.set import *

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

        self.failUnless(1 in x)
        self.failUnless('a' in y)
        self.failUnless( (1,2,3, (4,5)) in z)

        self.failf(0 in x)
        self.failf(0 in x)
        self.failf('A' in y)
        self.failf('z' in y)
        self.failf('a' in z)
        self.failf(1 in z)


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

