# Natural Language Toolkit: Test Code for Probability and Statistics
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.probability}.
"""

from nltk.probability import *
from nltk.set import Set

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

class FreqDistTestCase(unittest.TestCase):

    def setUp(self):
        # Construct an experiment:
        self.outcomes = '1 8 3 2 1 1 8 3 7 4 5 8 8 2 2'.split()
        self.bins = Set(*self.outcomes)

        # Record the experiment in a FreqDist.
        self.fdist = FreqDist()
        for outcome in self.outcomes:
            self.fdist.inc(outcome)

        # Fencepost case: empty distribution
        self.empty_fdist = FreqDist()

    def testN(self):
        'nltk.probability.FreqDistTestCase: test N()'
        self.failUnlessEqual(self.fdist.N(), len(self.outcomes))
        self.failUnlessEqual(self.empty_fdist.N(), 0)

    def testB(self):
        'nltk.probability.FreqDistTestCase: test B()'
        self.failUnlessEqual(self.fdist.B(), len(self.bins))
        self.failUnlessEqual(self.empty_fdist.B(), 0)

    def testSamples(self):
        'nltk.probability.FreqDistTestCase: test samples()'
        global z, b
        z = Set(*self.fdist.samples()), self.bins
        b = (z[0] == z[1])
        self.failUnlessEqual(Set(*self.fdist.samples()), self.bins)
        self.failUnlessEqual(self.empty_fdist.samples(), [])

    def testNr(self):
        'nltk.probability.FreqDistTestCase: test Nr()'
        self.failUnlessEqual(self.fdist.Nr(0), 0)
        self.failUnlessEqual(self.fdist.Nr(1), 3)
        self.failUnlessEqual(self.fdist.Nr(2), 1)
        self.failUnlessEqual(self.fdist.Nr(3), 2)
        self.failUnlessEqual(self.fdist.Nr(4), 1)
        self.failUnlessEqual(self.fdist.Nr(5), 0)

        self.failUnlessEqual(self.fdist.Nr(0, 15), 8)
        self.failUnlessEqual(self.fdist.Nr(1, 15), 3)
        self.failUnlessEqual(self.fdist.Nr(2, 15), 1)
        self.failUnlessEqual(self.fdist.Nr(3, 15), 2)
        self.failUnlessEqual(self.fdist.Nr(4, 15), 1)
        self.failUnlessEqual(self.fdist.Nr(5, 15), 0)

        self.failUnlessEqual(self.empty_fdist.Nr(0), 0)
        self.failUnlessEqual(self.empty_fdist.Nr(1), 0)
        self.failUnlessEqual(self.empty_fdist.Nr(2), 0)
        self.failUnlessEqual(self.empty_fdist.Nr(0, 5), 5)
        self.failUnlessEqual(self.empty_fdist.Nr(1, 5), 0)
        self.failUnlessEqual(self.empty_fdist.Nr(2, 5), 0)
        
        self.failUnlessRaises(IndexError, self.fdist.Nr, -1)
        self.failUnlessRaises(IndexError, self.empty_fdist.Nr, -1)
        self.failUnlessRaises(IndexError, self.fdist.Nr, -1, 15)
        self.failUnlessRaises(IndexError, self.empty_fdist.Nr, -1, 15)

    def testCount(self):
        'nltk.probability.FreqDistTestCase: test count()'
        self.failUnlessEqual(self.fdist.count('0'), 0)
        self.failUnlessEqual(self.fdist.count('1'), 3)
        self.failUnlessEqual(self.fdist.count('2'), 3)
        self.failUnlessEqual(self.fdist.count('3'), 2)
        self.failUnlessEqual(self.fdist.count('4'), 1)
        self.failUnlessEqual(self.fdist.count('5'), 1)
        self.failUnlessEqual(self.fdist.count('6'), 0)
        self.failUnlessEqual(self.fdist.count('7'), 1)
        self.failUnlessEqual(self.fdist.count('8'), 4)
        self.failUnlessEqual(self.fdist.count('9'), 0)
        self.failUnlessEqual(self.fdist.count(0), 0)
        
        self.failUnlessEqual(self.empty_fdist.count(0), 0)
        self.failUnlessEqual(self.empty_fdist.count('0'), 0)
        self.failUnlessEqual(self.empty_fdist.count('x'), 0)

    def testFreq(self):
        'nltk.probability.FreqDistTestCase: test freq()'
        N = float(len(self.outcomes))
        self.failUnlessEqual(self.fdist.freq('0'), 0/N)
        self.failUnlessEqual(self.fdist.freq('1'), 3/N)
        self.failUnlessEqual(self.fdist.freq('2'), 3/N)
        self.failUnlessEqual(self.fdist.freq('3'), 2/N)
        self.failUnlessEqual(self.fdist.freq('4'), 1/N)
        self.failUnlessEqual(self.fdist.freq('5'), 1/N)
        self.failUnlessEqual(self.fdist.freq('6'), 0/N)
        self.failUnlessEqual(self.fdist.freq('7'), 1/N)
        self.failUnlessEqual(self.fdist.freq('8'), 4/N)
        self.failUnlessEqual(self.fdist.freq('9'), 0/N)
        self.failUnlessEqual(self.fdist.freq(0), 0/N)

        self.failUnlessEqual(self.empty_fdist.freq(0), 0)
        self.failUnlessEqual(self.empty_fdist.freq('0'), 0)
        self.failUnlessEqual(self.empty_fdist.freq('x'), 0)

    def testMax(self):
        'nltk.probability.FreqDistTestCase: test max()'
        self.failUnlessEqual(self.fdist.max(), '8')

        # If there are 2 samples w/ the same freq, return one.
        fdist2 = FreqDist()
        for outcome in [0, 0, 1, 2, 3, 3]: fdist2.inc(outcome)
        self.failUnless(fdist2.max() in [0, 3])

        # If there are no samples, return None.
        self.failUnlessEqual(self.empty_fdist.max(), None)
        
class ConditionalFreqDistTestCase(unittest.TestCase):
    def setUp(self):
        self.cfdist = ConditionalFreqDist()
        pairs = ['aA', 'aB', 'cA', 'bC', 'aA', 'cA', 'cA', 'bA']
        for (condition, outcome) in pairs:
            self.cfdist[condition].inc(outcome)
            
    def testConditions(self):
        'nltk.probability.ConditionalFreqDistTestCase: test conditions()'
        self.failUnlessEqual(Set(*self.cfdist.conditions()),
                             Set('a', 'b', 'c'))

        # Accessing a condition adds it.
        self.cfdist['x']
        self.failUnlessEqual(Set(*self.cfdist.conditions()),
                             Set('a', 'b', 'c', 'x'))

    def testGetItem(self):
        'nltk.probability.ConditionalFreqDistTestCase: test __getitem__()'
        
        fdist_a = self.cfdist['a']
        self.failUnlessEqual(fdist_a.N(), 3)
        self.failUnlessEqual(fdist_a.count('A'), 2)
        self.failUnlessEqual(fdist_a.count('B'), 1)

        fdist_b = self.cfdist['b']
        self.failUnlessEqual(fdist_b.N(), 2)
        self.failUnlessEqual(fdist_b.count('A'), 1)
        self.failUnlessEqual(fdist_b.count('C'), 1)

        fdist_c = self.cfdist['c']
        self.failUnlessEqual(fdist_c.N(), 3)
        self.failUnlessEqual(fdist_c.count('A'), 3)

        fdist_d = self.cfdist['d']
        self.failUnlessEqual(fdist_d.N(), 0)

class UniformProbDistTestCase(unittest.TestCase):
    def setUp(self):
        self.pdist1 = UniformProbDist([1,3,2])
        self.pdist2 = UniformProbDist([3,1,1,1,1])
            
    def testProb(self):
        'nltk.probability.UniformProbDistTestCase: test prob()'
        self.failUnlessEqual(self.pdist1.prob(0), 0)
        self.failUnlessEqual(self.pdist1.prob(1), 1.0/3)
        self.failUnlessEqual(self.pdist1.prob(2), 1.0/3)
        self.failUnlessEqual(self.pdist1.prob(3), 1.0/3)

        self.failUnlessEqual(self.pdist2.prob(0), 0)
        self.failUnlessEqual(self.pdist2.prob(1), 1.0/2)
        self.failUnlessEqual(self.pdist2.prob(2), 0)
        self.failUnlessEqual(self.pdist2.prob(3), 1.0/2)

    def testLogProb(self):
        'nltk.probability.UniformProbDistTestCase: test prob()'
        import math
        self.failUnlessEqual(self.pdist1.logprob(1), math.log(1.0/3))
        self.failUnlessEqual(self.pdist1.logprob(2), math.log(1.0/3))
        self.failUnlessEqual(self.pdist1.logprob(3), math.log(1.0/3))

        self.failUnlessEqual(self.pdist2.logprob(1), math.log(1.0/2))
        self.failUnlessEqual(self.pdist2.logprob(3), math.log(1.0/2))
        
        self.failUnlessRaises(OverflowError, self.pdist1.logprob, 0)
        self.failUnlessRaises(OverflowError, self.pdist2.logprob, 0)
        self.failUnlessRaises(OverflowError, self.pdist2.logprob, 2)

    def testMax(self):
        'nltk.probability.UniformProbDistTestCase: test max()'
        self.failUnless(self.pdist1.max() in [1,2,3])
        self.failUnless(self.pdist2.max() in [1,3])

    def testSamples(self):
        'nltk.probability.UniformProbDistTestCase: test samples()'
        self.failUnlessEqual(Set(*self.pdist1.samples()), Set(1,2,3))
        self.failUnlessEqual(Set(*self.pdist2.samples()), Set(1,3))

    def testEmptyProbDist(self):
        'nltk.probability.UniformProbDistTestCase: test __init__()'
        self.failUnlessRaises(ValueError, UniformProbDist, [])

# Base class for testing prob dists
class ProbDistTestCase(unittest.TestCase):
    def make_probdist(self, fdist):
        raise AssertionError, 'abstract base class'

    PDIST_OUTCOMES = 'a list of lists of sample outcomes'
    PROB_MAPS = 'a list of dictionaries mapping samples to probs'
    MAXES = 'a list of maxes'

    def setUp(self):
        self.pdists = []
        for samples in self.PDIST_OUTCOMES:
            fdist = FreqDist()
            for sample in samples: fdist.inc(sample)
            self.pdists.append(self.make_probdist(fdist))
            
    def testProb(self):
        # Do *not* include a description string (subclassing)
        i = 0
        for (probmap, pdist) in zip(self.PROB_MAPS, self.pdists):
            for (sample, prob) in probmap.items():
                prob2 = pdist.prob(sample)
                msg = ('%r != %r\n    Context: pdist[%d].prob(%s)' %
                       (prob, prob2, i, sample))
                self.failUnlessEqual(prob, prob2, msg)
            i += 1

    def testLogProb(self):
        # Do *not* include a description string (subclassing)
        import math
        i = 0
        for (probmap, pdist) in zip(self.PROB_MAPS, self.pdists):
            for (sample, prob) in probmap.items():
                if prob>0:
                    logprob1 = math.log(prob)
                    logprob2 = pdist.logprob(sample)
                    msg = ('%r != %r\n    Context: pdist[%d].logprob(%s)' %
                           (logprob1, logprob2, i, sample))
                    self.failUnlessEqual(logprob1, logprob2, msg )
                else:
                    self.failUnlessRaises(OverflowError, pdist.logprob, sample)
            i += 1

    def testMax(self):
        # Do *not* include a description string (subclassing)
        for (max, pdist) in zip(self.MAXES, self.pdists):
            if type(max) in (type(()), type([])):
                self.failUnless(pdist.max() in max)
            else:
                self.failUnlessEqual(pdist.max(), max)

    def testSamples(self):
        # Do *not* include a description string (subclassing)
        for (samples, pdist) in zip(self.PDIST_OUTCOMES, self.pdists):
            self.failUnlessEqual(Set(*pdist.samples()), Set(*samples))

class MLEProbDistTestCase(ProbDistTestCase):
    def make_probdist(self, fdist):
        return MLEProbDist(fdist)

    PDIST_OUTCOMES = [[6,3,4,1,2,2,2,8,3,1],
                     [1,2,3,4,5,6,7,8,9,10],
                     [1,1,1,1,1]]
    MAXES = [2, (1,2,3,4,5,6,7,8,9,10), 1]
    
    PROB_MAPS = [{0:0./10, 1:2./10, 2:3./10, 3:2./10, 4:1./10, 5:0./16,
                  6:1./10, 7:0./10},
                 
                 {0:0./10, 1:1./10, 2:1./10, 3:1./10, 4:1./10, 5:1./10,
                  6:1./10, 7:1./10, 8:1./10, 9:1./10, 10:1./10, 11:0./10},
                 
                 {0:0./1, 1:1/1, 2:0./1}]

class LaplaceProbDistTestCase(ProbDistTestCase):
    def make_probdist(self, fdist):
        return LaplaceProbDist(fdist)

    PDIST_OUTCOMES = [[6,3,4,1,2,2,2,8,3,1], # 6 bins
                     [1,2,3,4,5,6,7,8,9,10], # 10 bins
                     [1,1,1,1,1]] # 1 bin
    MAXES = [2, (1,2,3,4,5,6,7,8,9,10), 1]
    
    PROB_MAPS = [{0:1./16, 1:3./16, 2:4./16, 3:3./16, 4:2./16, 5:1./16,
                  6:2./16, 7:1./16},
                 
                 {0:1./20, 1:2./20, 2:2./20, 3:2./20, 4:2./20, 5:2./20,
                  6:2./20, 7:2./20, 8:2./20, 9:2./20, 10:2./20, 11:1./20},
                 
                 {0:1./6, 1:6./6, 2:1./6}]

class ELEProbDistTestCase(ProbDistTestCase):
    def make_probdist(self, fdist):
        return ELEProbDist(fdist)

    PDIST_OUTCOMES = [[6,3,4,1,2,2,2,8,3,1], # 6 bins
                     [1,2,3,4,5,6,7,8,9,10], # 10 bins
                     [1,1,1,1,1]] # 1 bin
    MAXES = [2, (1,2,3,4,5,6,7,8,9,10), 1]
    
    PROB_MAPS = [{0:0.5/13, 1:2.5/13, 2:3.5/13, 3:2.5/13, 4:1.5/13, 5:0.5/13,
                  6:1.5/13, 7:0.5/13},
                 
                 {0:0.5/15, 1:1.5/15, 2:1.5/15, 3:1.5/15, 4:1.5/15,
                  5:1.5/15, 6:1.5/15, 7:1.5/15, 8:1.5/15, 9:1.5/15,
                  10:1.5/15, 11:0.5/15},
                 
                 {0:0.5/5.5, 1:5.5/5.5, 2:0.5/5.5}]

class Laplace20BinProbDistTestCase(ProbDistTestCase):
    def make_probdist(self, fdist):
        return LaplaceProbDist(fdist, 20)

    PDIST_OUTCOMES = [[6,3,4,1,2,2,2,8,3,1], # 20 bins
                     [1,2,3,4,5,6,7,8,9,10], # 20 bins
                     [1,1,1,1,1]] # 20 bin
    MAXES = [2, (1,2,3,4,5,6,7,8,9,10), 1]
    
    PROB_MAPS = [{0:1./30, 1:3./30, 2:4./30, 3:3./30, 4:2./30, 5:1./30,
                  6:2./30, 7:1./30},
                 
                 {0:1./30, 1:2./30, 2:2./30, 3:2./30, 4:2./30, 5:2./30,
                  6:2./30, 7:2./30, 8:2./30, 9:2./30, 10:2./30, 11:1./30},
                 
                 {0:1./25, 1:6.0/25, 2:1./25}]

class ELE20BinProbDistTestCase(ProbDistTestCase):
    def make_probdist(self, fdist):
        return ELEProbDist(fdist, 20)

    PDIST_OUTCOMES = [[6,3,4,1,2,2,2,8,3,1], # 20 bins
                     [1,2,3,4,5,6,7,8,9,10], # 20 bins
                     [1,1,1,1,1]] # 20 bin
    MAXES = [2, (1,2,3,4,5,6,7,8,9,10), 1]
    
    PROB_MAPS = [{0:0.5/20, 1:2.5/20, 2:3.5/20, 3:2.5/20, 4:1.5/20, 5:0.5/20,
                  6:1.5/20, 7:0.5/20},
                 
                 {0:0.5/20, 1:1.5/20, 2:1.5/20, 3:1.5/20, 4:1.5/20,
                  5:1.5/20, 6:1.5/20, 7:1.5/20, 8:1.5/20, 9:1.5/20,
                  10:1.5/20, 11:0.5/20},
                 
                 {0:0.5/15, 1:5.5/15, 2:0.5/15}]

def testsuite():
    """
    Return a PyUnit testsuite for the probability module.
    """

    t1 = unittest.makeSuite(FreqDistTestCase)
    t2 = unittest.makeSuite(ConditionalFreqDistTestCase)
    t3 = unittest.makeSuite(UniformProbDistTestCase)
    t4 = unittest.makeSuite(MLEProbDistTestCase)
    t5 = unittest.makeSuite(LaplaceProbDistTestCase)
    t6 = unittest.makeSuite(ELEProbDistTestCase)
    t7 = unittest.makeSuite(Laplace20BinProbDistTestCase)
    t8 = unittest.makeSuite(ELE20BinProbDistTestCase)
    return unittest.TestSuite( (t1, t2, t3, t4, t5, t6, t7, t8, ) )

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()

