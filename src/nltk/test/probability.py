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

@group Frequency Distributions: test_FreqDist
@group Probability Distributions: test_*ProbDist*
"""

from nltk.probability import *
from nltk.util import mark_stdout_newlines
import random

def test_FreqDist(): """
Unit tests for L{FreqDist}

A frequency distribution records the outcomes of an experiment.  It is
empty when it is constructed:

    >>> fdist = FreqDist()
    >>> fdist
    <FreqDist with 0 samples>

Sample outcomes are recorded with C{inc}:

    >>> outcomes = 'A H C B A A H C G D E H H B B'.split()
    >>> for outcome in outcomes:
    ...     fdist.inc(outcome)
    >>> fdist
    <FreqDist with 15 samples>
    >>> print fdist
    <FreqDist: 'H': 4, 'A': 3, 'B': 3, 'C': 2, 'D': 1, 'E': 1, 'G': 1>

The count for a given sample is returned by C{count}:

    >>> fdist.count('A')
    3
    >>> fdist.count('D')
    1
    >>> fdist.count('Z')
    0

The frequency of a given sample is returned by C{freq}:

    >>> print '%.4f' % fdist.freq('A')
    0.2000
    >>> print '%.4f' % fdist.freq('D')
    0.0667
    >>> print '%.4f' % fdist.freq('Z')
    0.0000

The most frequent sample is returned by C{max}

    >>> fdist.max()
    'H'

The number of sample outcomes is returned by C{N}:

    >>> fdist.N()
    15

The number of sample values (or bins) is returned by C{B}:

    >>> fdist.B()
    7

The set of sample values with nonzero counts are returned by
C{samples}, in undefined order:

    >>> samples = fdist.samples()
    >>> samples.sort()
    >>> samples
    ['A', 'B', 'C', 'D', 'E', 'G', 'H']

C{sorted_samples} returns a list of the samples, sorted in order of
decreasing frequency:

   >>> print fdist.sorted_samples()
   ['H', 'A', 'B', 'C', 'D', 'E', 'G']

The number of samples with a given count is returned by C{Nr}:

    >>> fdist.Nr(1)
    3
    >>> fdist.Nr(2)
    1
    >>> fdist.Nr(3)
    2

C{Nr(0)} can be calculated if the number of bins is supplied:

    >>> fdist.Nr(0, 10)
    3

It is an error to call C{Nr} with C{r<0}:

    >>> fdist.Nr(-1)
    Traceback (most recent call last):
      [...]
    IndexError: FreqDist.Nr(): r must be non-negative

The C{in} operator can be used to test if a sample has a nonzero
count:

    >>> print 'A' in fdist
    True
    >>> print 'Z' in fdist
    False

"""

def test_ProbDistI(): r"""
Unit tests for L{ProbDistI}.

C{ProbDistI} is an interface for probability distributions.

    >>> ProbDistI()
    Traceback (most recent call last):
      [...]
    AssertionError: Interfaces can't be instantiated

It declares 4 methods, which must be implemented by derived classes:

    >>> class BrokenProbDist(ProbDistI):
    ...     pass
    >>> BrokenProbDist().prob('A')
    Traceback (most recent call last):
      [...]
    AssertionError
    >>> BrokenProbDist().logprob('A')
    Traceback (most recent call last):
      [...]
    AssertionError
    >>> BrokenProbDist().max()
    Traceback (most recent call last):
      [...]
    AssertionError
    >>> BrokenProbDist().samples()
    Traceback (most recent call last):
      [...]
    AssertionError
"""

def test_UniformProbDist(): r"""
Unit tests for L{UniformProbDist}.

A uniform probability distribution is constructed from a list of
samples:

    >>> samples = 'A B C D E F G H'.split()
    >>> pdist = UniformProbDist(samples)
    >>> print pdist
    <UniformProbDist with 8 samples>

It assigns equal probability to all samples:

    >>> samples = pdist.samples(); samples.sort(); print samples
    ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    >>> for sample in samples:
    ...     print 'P(%r) = %s' % (sample, pdist.prob(sample))
    P('A') = 0.125
    P('B') = 0.125
    P('C') = 0.125
    P('D') = 0.125
    P('E') = 0.125
    P('F') = 0.125
    P('G') = 0.125
    P('H') = 0.125

C{max} returns an arbitrary sample from the samples:

    >>> pdist.max() in pdist.samples()
    True

Any duplicates given to the constructor are ignored:

    >>> samples = 'A B C D E F G H A B B A C A H H H'.split()
    >>> pdist = UniformProbDist(samples)
    >>> print pdist
    <UniformProbDist with 8 samples>

    >>> samples = pdist.samples(); samples.sort(); print samples
    ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    >>> for sample in samples:
    ...     print 'P(%r) = %s' % (sample, pdist.prob(sample))
    P('A') = 0.125
    P('B') = 0.125
    P('C') = 0.125
    P('D') = 0.125
    P('E') = 0.125
    P('F') = 0.125
    P('G') = 0.125
    P('H') = 0.125
"""

def test_DictionaryProbDist(): r"""
Unit tests for L{DictionaryProbDist}.

A dictionary probability distribution is constructed from a dictionary
that maps samples to probabilities:

    >>> sampledict = {'A': 0.25, 'B': 0.5, 'C': 0.125, 'D': 0.125}
    >>> pdist = DictionaryProbDist(sampledict)
    >>> print pdist
    <ProbDist with 4 samples>

    >>> samples = pdist.samples(); samples.sort(); print samples
    ['A', 'B', 'C', 'D']
    >>> for sample in samples:
    ...     print 'P(%r) = %s' % (sample, pdist.prob(sample))
    P('A') = 0.25
    P('B') = 0.5
    P('C') = 0.125
    P('D') = 0.125

    >>> pdist.max()
    'B'
"""

def test_MLEProbDist(): r"""
Unit tests for L{MLEProbDist}.

An MLE probability distribution is constructed from an underlying
frequency distribution:

    >>> fdist = FreqDist()
    >>> for outcome in 'A H C B A A H C G D E H H B B D'.split():
    ...     fdist.inc(outcome)

    >>> pdist = MLEProbDist(fdist)
    >>> print pdist
    <MLEProbDist based on 16 samples>

The probability of a sample is equal to its frequency:

    >>> samples = pdist.samples(); samples.sort(); print samples
    ['A', 'B', 'C', 'D', 'E', 'G', 'H']
    >>> for sample in samples:
    ...     print 'P(%r) = %s' % (sample, pdist.prob(sample))
    P('A') = 0.1875
    P('B') = 0.1875
    P('C') = 0.125
    P('D') = 0.125
    P('E') = 0.0625
    P('G') = 0.0625
    P('H') = 0.25

    >>> pdist.max()
    'H'
"""

def test_LidstoneProbDist(): r"""
Unit tests for L{LidstoneProbDist}.

An Lidstone probability distribution is constructed from an underlying
frequency distribution, a gamma, and optionally a number of bins:

    >>> fdist = FreqDist()
    >>> for outcome in 'A B A A A C A B A D A A C A C'.split():
    ...     fdist.inc(outcome)

    >>> pdist = LidstoneProbDist(fdist, 0.25, 4)
    >>> print pdist
    <LidstoneProbDist based on 15 samples>

The probability of a sample is equal to its frequency:

    >>> samples = pdist.samples(); samples.sort(); print samples
    ['A', 'B', 'C', 'D']
    >>> for sample in samples:
    ...     print 'P(%r) = %s' % (sample, pdist.prob(sample))
    P('A') = 0.578125
    P('B') = 0.140625
    P('C') = 0.203125
    P('D') = 0.078125

    >>> pdist.max()
    'A'

The underlying frequency distribution can be accessed with C{freqdist}:

    >>> print pdist.freqdist()
    <FreqDist: 'A': 9, 'C': 3, 'B': 2, 'D': 1>
"""

def test_LidstoneProbDist(): r"""
Unit tests for L{LidstoneProbDist}.

An Lidstone probability distribution is constructed from an underlying
frequency distribution and optionally a number of bins:

    >>> fdist = FreqDist()
    >>> for outcome in 'A B A A B A A B A D A A C D'.split():
    ...     fdist.inc(outcome)

    >>> pdist = LidstoneProbDist(fdist, 4)
    >>> print pdist
    <LidstoneProbDist based on 14 samples>

The probability of a sample is equal to its frequency:

    >>> samples = pdist.samples(); samples.sort(); print samples
    ['A', 'B', 'C', 'D']
    >>> for sample in samples:
    ...     print 'P(%r) = %.4f' % (sample, pdist.prob(sample))
    P('A') = 0.4000
    P('B') = 0.2333
    P('C') = 0.1667
    P('D') = 0.2000

    >>> pdist.max()
    'A'

The underlying frequency distribution can be accessed with C{freqdist}:

    >>> print pdist.freqdist()
    <FreqDist: 'A': 8, 'B': 3, 'D': 2, 'C': 1>
"""

def test_ELEProbDist(): r"""
Unit tests for L{ELEProbDist}.

An ELE probability distribution is constructed from an underlying
frequency distribution and optionally a number of bins:

    >>> fdist = FreqDist()
    >>> for outcome in 'A B A A B A A B A D A A C D'.split():
    ...     fdist.inc(outcome)

    >>> pdist = ELEProbDist(fdist, 4)
    >>> print pdist
    <ELEProbDist based on 14 samples>

The probability of a sample is equal to its frequency:

    >>> samples = pdist.samples(); samples.sort(); print samples
    ['A', 'B', 'C', 'D']
    >>> for sample in samples:
    ...     print 'P(%r) = %.4f' % (sample, pdist.prob(sample))
    P('A') = 0.5312
    P('B') = 0.2188
    P('C') = 0.0938
    P('D') = 0.1562

    >>> pdist.max()
    'A'

The underlying frequency distribution can be accessed with C{freqdist}:

    >>> print pdist.freqdist()
    <FreqDist: 'A': 8, 'B': 3, 'D': 2, 'C': 1>
"""

def test_HeldoutProbDist(): r"""
Unit tests for L{HeldoutProbDist}

(to be written)
"""

def test_CrossValidationProbDist(): r"""
Unit tests for L{CrossValidationProbDist}

(to be written)
"""

def test_WittenBellProbDist(): r"""
Unit tests for L{WittenBellProbDist}

(to be written)
"""

def test_GoodTuringProbDist(): r"""
Unit tests for L{GoodTuringProbDist}

(to be written)
"""

def test_ConditionalFreqDist(): r"""
Unit tests for L{ConditionalFreqDist}

(to be written)
"""

def test_ConditionalProbDistI(): r"""
Unit tests for L{ConditionalProbDistI}

(to be written)
"""

def test_ConditionalProbDist(): r"""
Unit tests for L{ConditionalProbDist}

(to be written)
"""

def test_ProbabilisticMixIn(): r"""
Unit tests for L{ProbabilisticMixIn}

(to be written)
"""

def test_demo(): r"""
Unit tests for L{nltk.probability.demo}.

    >>> random.seed(123456)
    >>> mark_stdout_newlines(demo)
    6 samples (1-6); 500 outcomes were sampled for each FreqDist
    ========================================================================
          FreqDist MLEProbD Lidstone HeldoutP HeldoutP CrossVal |  Actual
    ------------------------------------------------------------------------
      1   0.082000 0.082000 0.082505 0.078000 0.082000 0.084000 | 0.083333
      2   0.164000 0.164000 0.164016 0.172000 0.181000 0.175667 | 0.166667
      3   0.238000 0.238000 0.237575 0.250000 0.238000 0.242000 | 0.250000
      4   0.246000 0.246000 0.245527 0.248000 0.246000 0.238667 | 0.250000
      5   0.198000 0.198000 0.197813 0.172000 0.181000 0.184333 | 0.166667
      6   0.072000 0.072000 0.072565 0.080000 0.072000 0.075333 | 0.083333
    ------------------------------------------------------------------------
    Total 1.000000 1.000000 1.000000 1.000000 1.000000 1.000000 | 1.000000
    ========================================================================
      fdist1: <FreqDist: 4: 123, 3: 119, 5: 99, 2: 82, 1: 41, 6: 36>
      fdist2: <FreqDist: 3: 125, 4: 124, 2: 86, 5: 86, 6: 40, 1: 39>
      fdist3: <FreqDist: 3: 119, 4: 111, 5: 98, 2: 89, 1: 46, 6: 37>
    <--BLANKLINE-->

    >>> random.seed(654321)
    >>> mark_stdout_newlines(demo)
    6 samples (1-6); 500 outcomes were sampled for each FreqDist
    ========================================================================
          FreqDist MLEProbD Lidstone HeldoutP HeldoutP CrossVal |  Actual
    ------------------------------------------------------------------------
      1   0.082000 0.082000 0.082505 0.096000 0.082000 0.085333 | 0.083333
      2   0.202000 0.202000 0.201789 0.142000 0.202000 0.170000 | 0.166667
      3   0.234000 0.234000 0.233598 0.268000 0.234000 0.256000 | 0.250000
      4   0.236000 0.236000 0.235586 0.254000 0.236000 0.246000 | 0.250000
      5   0.160000 0.160000 0.160040 0.152000 0.160000 0.157333 | 0.166667
      6   0.086000 0.086000 0.086481 0.088000 0.086000 0.085333 | 0.083333
    ------------------------------------------------------------------------
    Total 1.000000 1.000000 1.000000 1.000000 1.000000 1.000000 | 1.000000
    ========================================================================
      fdist1: <FreqDist: 4: 118, 3: 117, 2: 101, 5: 80, 6: 43, 1: 41>
      fdist2: <FreqDist: 3: 134, 4: 127, 5: 76, 2: 71, 1: 48, 6: 44>
      fdist3: <FreqDist: 3: 133, 4: 124, 2: 83, 5: 80, 6: 41, 1: 39>
    <--BLANKLINE-->
    """

#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite(reload_module=False):
    import doctest, nltk.test.probability
    if reload_module: reload(nltk.test.probability)
    return doctest.DocTestSuite(nltk.test.probability)

def test(verbosity=2, reload_module=False):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite(reload_module))

if __name__ == '__main__':
    test(reload_module=True)
