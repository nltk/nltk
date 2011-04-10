# Natural Language Toolkit: Evaluation
#
# Copyright (C) 2001-2011 NLTK Project
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

import nltk

from util import LazyConcatenation, LazyMap, LazyZip
from probability import FreqDist

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
