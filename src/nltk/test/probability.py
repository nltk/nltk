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

class CFFreqDistTestCase(unittest.TestCase):
    """
    Unit test cases for C{nltk.probability.CFFreqDist}.
    These tests are nondeterministic, and assume that
    nltk.probability.SimpleFreqDist is working correctly.
    """
    seed = 12347
    
    def __init__(self, *args, **kwargs):
        # Call parent constructor.
        unittest.TestCase.__init__(self, *args, **kwargs)
        
        # Build frequency distributions; we'll copy them for each
        # test.
        import random

        random.seed(CFFreqDistTestCase.seed)
        CFFreqDistTestCase.seed += 2343
        
        self._NUM_CONTEXTS = 5
        self._NUM_FEATURES = 5

        self._freqdist1 = CFFreqDist()
        self._freqdist2 = SimpleFreqDist()

        for x in range(100):
            context = random.randint(1,self._NUM_CONTEXTS)
            feature = str(random.randint(1,self._NUM_FEATURES))
            sample = CFSample(context, feature)
            self._freqdist1.inc(sample)
            self._freqdist2.inc(sample)
        print self._freqdist1
    
    def setUp(self):
        import copy
        self._fdist1 = copy.deepcopy(self._freqdist1)
        self._fdist2 = copy.deepcopy(self._freqdist2)
        
    def testSamples(self):
        "nltk.probability.CFFreqDist.samples() test"
        samples1 = self._fdist1.samples()[:]
        samples2 = self._fdist2.samples()[:]
        samples1.sort()
        samples2.sort()
        self.failUnlessEqual(samples1, samples2)

    def testCount(self):
        "nltk.probability.CFFreqDist.count() test"
        for sample in self._fdist1.samples():
            self.failUnlessEqual(self._fdist1.count(sample),
                                 self._fdist2.count(sample))

    def testFreq(self):
        "nltk.probability.CFFreqDist.freq() test"
        for sample in self._fdist1.samples():
            self.failUnlessEqual(self._fdist1.freq(sample),
                                 self._fdist2.freq(sample))
        
    def testCondFreq(self):
        "nltk.probability.CFFreqDist.cond_freq() test"
        for context in range(1, self._NUM_CONTEXTS+1):
            e=ContextEvent(context)
            for feature in range(1, self._NUM_FEATURES+1):
                s=CFSample(context, str(feature))
                self.failUnlessEqual(self._fdist1.cond_freq(s,e),
                                     self._fdist2.cond_freq(s,e))

    def testCondMax(self):
        "nltk.probability.CFFreqDist.cond_max() test"
        for context in range(1, self._NUM_CONTEXTS+1):
            e=ContextEvent(context)
            max1 = self._fdist1.cond_max(e)
            max2 = self._fdist2.cond_max(e)
            self.failUnlessEqual(self._fdist2.freq(max1),
                                 self._fdist2.freq(max2))

    def testMax(self):
        "nltk.probability.CFFreqDist.max() test"
        max1 = self._fdist1.max()
        max2 = self._fdist2.max()
        self.failUnlessEqual(self._fdist2.freq(max1),
                             self._fdist2.freq(max2))
        
    def testN(self):
        "nltk.probability.CFFreqDist.N() test"
        self.failUnlessEqual(self._fdist1.N(), self._fdist2.N())
        
    def testB(self):
        "nltk.probability.CFFreqDist.B() test"
        self.failUnlessEqual(self._fdist1.B(), self._fdist2.B())
        
    def testNr(self):
        "nltk.probability.CFFreqDist.Nr() test"
        for r in range(20):
            self.failUnlessEqual(self._fdist1.Nr(r), self._fdist2.Nr(r))

def testsuite():
    """
    Return a PyUnit testsuite for the probability module.
    """
    
    tests = unittest.TestSuite((
        unittest.makeSuite(SampleEventTestCase, 'test'),

        # Include CFFreqDist 3 times, since it uses nondeterministic
        # tests.
        unittest.makeSuite(CFFreqDistTestCase, 'test'),
        unittest.makeSuite(CFFreqDistTestCase, 'test'),
        unittest.makeSuite(CFFreqDistTestCase, 'test'),
        ))

    return tests

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()

