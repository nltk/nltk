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

_SMOOTHING = .000001


class TrigramAssociationMeasureI(object):
    """Interface for a trigram association measure function"""
    def __call__(self, n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
        raise AssertionError, "This is an interface"


def _contingency(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    """Calculates values of a trigram contingency table (or cube)."""
    n_oii = n_xii - n_iii
    n_ioi = n_ixi - n_iii
    n_iio = n_iix - n_iii
    n_ooi = n_xxi - n_iii - n_oii - n_ioi
    n_oio = n_xix - n_iii - n_oii - n_iio
    n_ioo = n_ixx - n_iii - n_ioi - n_iio
    n_ooo = n_xxx - n_iii - n_oii - n_ioi - n_iio - n_ooi - n_oio - n_ioo
    return (n_iii, n_oii, n_ioi, n_ooi,
            n_iio, n_oio, n_ioo, n_ooo)


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
    return _ln(n_iii * n_xxx) - _ln(n_ixx * n_xix * n_xxi)


def student_t(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    """Scores trigrams using Student's t test with independence hypothesis
    for unigrams.
    """
    return ((n_iii - (n_ixx * n_xix * n_xxi) / (n_xxx * n_xxx)) /
            (n_iii + _SMOOTHING) ** .5)


_product = lambda s: reduce(lambda x,y:x*y, s)
def chi_sq(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    """Scores trigrams using Pearson's chi-square."""

    cont = _contingency(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx)

    res = 0
    # For each contingency cube cell
    for i in range(8):
        Ei = _product((cont[i] + cont[i ^ j]) for j in (1,2,4)) / float(n_xxx)
        res += (cont[i] - Ei) ** 2 / (Ei + _SMOOTHING)
    return res


