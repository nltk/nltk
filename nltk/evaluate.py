# Natural Language Toolkit: Evaluation
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
Utility functions for evaluating processing modules.
"""

import sys
import math
import random

try:
    from scipy.stats.stats import betai
except ImportError:
    betai = None

from nltk import metrics

from util import LazyConcatenation, LazyMap, LazyZip
from probability import FreqDist
from internals import deprecated

@deprecated('Use nltk.metrics.accuracy() instead.')
def accuracy(reference, test):
    return metrics.accuracy(reference, test) 

@deprecated('Use nltk.metrics.precision()instead.')
def precision(reference, test):
    return metrics.precision(reference, test)

@deprecated('Use nltk.metrics.recall() instead.')
def recall(reference, test):
    return metrics.recall(reference, test)

@deprecated('Use nltk.metrics.f_measure() instead.')
def f_measure(reference, test, alpha=0.5):
    return metrics.f_measure(reference, test, alpha)

@deprecated('Use nltk.metrics.log_likelihood() instead.')
def log_likelihood(reference, test):
    return metrics.log_likelihood(reference, test)

@deprecated('Use nltk.metrics.approxrand() instead.')
def approxrand(a, b, **kwargs):
    return nltk.metrics.approxrand(a, b, **kwargs)

class ConfusionMatrix(metrics.ConfusionMatrix):
    @deprecated('Use nltk.metrics.ConfusionMatrix instead.')
    def __init__(self, reference, test, sort_by_count=False):
        metrics.ConfusionMatrix.__init__(self, reference, test, sort_by_count)

@deprecated('Use nltk.metrics.windowdiff instead.')
def windowdiff(seg1, seg2, k, boundary="1"):
    return metrics.windowdiff(seg1, seg2, k, boundary)

@deprecated('Use nltk.metrics.edit_dist instead.')
def edit_dist(s1, s2):
    return metrics.edit_dist(s1, s2)

def demo():
    print '-'*75
    reference = 'DET NN VB DET JJ NN NN IN DET NN'.split()
    test    = 'DET VB VB DET NN NN NN IN DET NN'.split()
    print 'Reference =', reference
    print 'Test    =', test
    print 'Confusion matrix:'
    print ConfusionMatrix(reference, test)
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

__all__ = ['ConfusionMatrix', 'accuracy',
           'f_measure', 'log_likelihood', 'precision', 'recall',
           'approxrand', 'edit_dist', 'windowdiff']
