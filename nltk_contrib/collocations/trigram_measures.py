# Natural Language Toolkit: Trigram Association Measures
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
"""
A number of functions to score trigram associations. Each association measure
is provided as a function with eight arguments:
    trigram_score_fn(n_iii, n_ixx, n_xix, n_xxi, n_iix, n_ixi, n_xii, n_xxx)
Each argument counts the occurrences of a particular event in a corpus. The
letter i in the suffix refers to the appearance of the word in question, while
x indicates to the appearance of any word. Thus, for example:
n_iii counts (w1, w2, w3), i.e. the trigram being scored
n_ixx counts (w1, *, *)
n_xxx counts (*, *, *), i.e. any trigram
"""

import math as _math
_ln = lambda x: _math.log(x, 2.0)


class TrigramAssociationMeasureI(object):
    """Interface for a trigram association measure function"""
    def __call__(self, n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
        raise AssertionError, "This is an interface"


def raw_freq(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    """Scores trigrams by their frequency"""
    return float(n_iii) / n_xxx


def pmi(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    """Scores trigrams by pointwise mutual information"""
    return _ln(n_ixx * n_xix * nxxi) - 2*_ln(n_xxx)


