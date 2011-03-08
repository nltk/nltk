# Natural Language Toolkit: Evaluation
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


import sys
import math
import random

try:
    from scipy.stats.stats import betai
except ImportError:
    betai = None

from nltk.util import LazyConcatenation, LazyMap
from itertools import izip
from nltk.probability import FreqDist

def accuracy(reference, test):
    """
    Given a list of reference values and a corresponding list of test
    values, return the fraction of corresponding values that are
    equal.  In particular, return the fraction of indices
    C{0<i<=len(test)} such that C{test[i] == reference[i]}.

    @type reference: C{list}
    @param reference: An ordered list of reference values.
    @type test: C{list}
    @param test: A list of values to compare against the corresponding
        reference values.
    @raise ValueError: If C{reference} and C{length} do not have the
        same length.
    """
    if len(reference) != len(test):
        raise ValueError("Lists must have the same length.")
    num_correct = 0
    for x, y in izip(reference, test):
        if x == y:
            num_correct += 1
    return float(num_correct) / len(reference)

def precision(reference, test):
    """
    Given a set of reference values and a set of test values, return
    the fraction of test values that appear in the reference set.
    In particular, return |C{reference}S{cap}C{test}|/|C{test}|.
    If C{test} is empty, then return C{None}.
    
    @type reference: C{Set}
    @param reference: A set of reference values.
    @type test: C{Set}
    @param test: A set of values to compare against the reference set.
    @rtype: C{float} or C{None}
    """
    if (not hasattr(reference, 'intersection') or
        not hasattr(test, 'intersection')):
        raise TypeError('reference and test should be sets')
    
    if len(test) == 0:
        return None
    else:
        return float(len(reference.intersection(test)))/len(test)

def recall(reference, test):
    """
    Given a set of reference values and a set of test values, return
    the fraction of reference values that appear in the test set.
    In particular, return |C{reference}S{cap}C{test}|/|C{reference}|.
    If C{reference} is empty, then return C{None}.
    
    @type reference: C{Set}
    @param reference: A set of reference values.
    @type test: C{Set}
    @param test: A set of values to compare against the reference set.
    @rtype: C{float} or C{None}
    """
    if (not hasattr(reference, 'intersection') or
        not hasattr(test, 'intersection')):
        raise TypeError('reference and test should be sets')
    
    if len(reference) == 0:
        return None
    else:
        return float(len(reference.intersection(test)))/len(reference)

def f_measure(reference, test, alpha=0.5):
    """
    Given a set of reference values and a set of test values, return
    the f-measure of the test values, when compared against the
    reference values.  The f-measure is the harmonic mean of the
    L{precision} and L{recall}, weighted by C{alpha}.  In particular,
    given the precision M{p} and recall M{r} defined by:
        - M{p} = |C{reference}S{cap}C{test}|/|C{test}|
        - M{r} = |C{reference}S{cap}C{test}|/|C{reference}|
    The f-measure is:
        - 1/(C{alpha}/M{p} + (1-C{alpha})/M{r})
        
    If either C{reference} or C{test} is empty, then C{f_measure}
    returns C{None}.
    
    @type reference: C{Set}
    @param reference: A set of reference values.
    @type test: C{Set}
    @param test: A set of values to compare against the reference set.
    @rtype: C{float} or C{None}
    """
    p = precision(reference, test)
    r = recall(reference, test)
    if p is None or r is None:
        return None
    if p == 0 or r == 0:
        return 0
    return 1.0/(alpha/p + (1-alpha)/r)

def log_likelihood(reference, test):
    """
    Given a list of reference values and a corresponding list of test
    probability distributions, return the average log likelihood of
    the reference values, given the probability distributions.

    @param reference: A list of reference values
    @type reference: C{list}
    @param test: A list of probability distributions over values to
        compare against the corresponding reference values.
    @type test: C{list} of L{ProbDistI}
    """
    if len(reference) != len(test):
        raise ValueError("Lists must have the same length.")

    # Return the average value of dist.logprob(val).
    total_likelihood = sum(dist.logprob(val)
                            for (val, dist) in zip(reference, test))
    return total_likelihood/len(reference)

def approxrand(a, b, **kwargs):
    """
    Returns an approximate significance level between two lists of
    independently generated test values.
    
    Approximate randomization calculates significance by randomly drawing
    from a sample of the possible permutations. At the limit of the number
    of possible permutations, the significance level is exact. The
    approximate significance level is the sample mean number of times the
    statistic of the permutated lists varies from the actual statistic of
    the unpermuted argument lists.
    
    @return: a tuple containing an approximate significance level, the count
             of the number of times the pseudo-statistic varied from the
             actual statistic, and the number of shuffles
    @rtype: C{tuple}
    @param a: a list of test values
    @type a: C{list}
    @param b: another list of independently generated test values
    @type b: C{list}
    """
    shuffles = kwargs.get('shuffles', 999)
    # there's no point in trying to shuffle beyond all possible permutations
    shuffles = \
        min(shuffles, reduce(lambda x, y: x * y, xrange(1, len(a) + len(b) + 1)))
    stat = kwargs.get('statistic', lambda lst: float(sum(lst)) / len(lst))
    verbose = kwargs.get('verbose', False)
    
    if verbose:
        print 'shuffles: %d' % shuffles
    
    actual_stat = math.fabs(stat(a) - stat(b))
    
    if verbose:
        print 'actual statistic: %f' % actual_stat
        print '-' * 60
    
    c = 1e-100
    lst = LazyConcatenation([a, b])
    indices = range(len(a) + len(b))

    for i in range(shuffles):
        if verbose and i % 10 == 0:
            print 'shuffle: %d' % i

        random.shuffle(indices)
        
        pseudo_stat_a = stat(LazyMap(lambda i: lst[i], indices[:len(a)]))
        pseudo_stat_b = stat(LazyMap(lambda i: lst[i], indices[len(a):]))
        pseudo_stat = math.fabs(pseudo_stat_a - pseudo_stat_b)
        
        if pseudo_stat >= actual_stat:
            c += 1
            
        if verbose and i % 10 == 0:
            print 'pseudo-statistic: %f' % pseudo_stat
            print 'significance: %f' % (float(c + 1) / (i + 1))
            print '-' * 60
        
    significance = float(c + 1) / (shuffles + 1)
    
    if verbose:
        print 'significance: %f' % significance        
        if betai:
            for phi in [0.01, 0.05, 0.10, 0.15, 0.25, 0.50]:
                print "prob(phi<=%f): %f" % (phi, betai(c, shuffles, phi))
    
    return (significance, c, shuffles)


def demo():
    print '-'*75
    reference = 'DET NN VB DET JJ NN NN IN DET NN'.split()
    test    = 'DET VB VB DET NN NN NN IN DET NN'.split()
    print 'Reference =', reference
    print 'Test    =', test
    print 'Accuracy:', accuracy(reference, test)

    print '-'*75
    reference_set = set(reference)
    test_set = set(test)
    print 'Reference =', reference_set
    print 'Test =   ', test_set
    print 'Precision:', precision(reference_set, test_set)
    print '   Recall:', recall(reference_set, test_set)
    print 'F-Measure:', f_measure(reference_set, test_set)
    print '-'*75

if __name__ == '__main__':
    demo()

