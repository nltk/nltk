# Natural Language Toolkit: Bigram Association Measures
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
"""
A number of functions to score bigram associations. Each association measure
is provided as a function with four arguments:
    bigram_score_fn(n_ii, n_ix, n_xi, n_xx)
Each argument counts the occurrences of a particular event in a corpus. The
letter i in the suffix refers to the appearance of the word in question, while
x indicates to the appearance of any word. Thus:
n_ii counts (w1, w2), i.e. the bigram being scored
n_ix counts (w1, *)
n_xi counts (*, w2)
n_xx counts (*, *), i.e. any bigram
"""

import math as _math
_ln = lambda x: _math.log(x, 2.0)

_SMOOTHING = .000001


class BigramAssociationMeasureI(object):
    """Interface for a bigram association measure function"""
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        raise AssertionError, "This is an interface"


def _contingency(n_ii, n_ix, n_xi, n_xx):
    """Calculates values of a bigram contingency table."""
    n_oi = n_xi - n_ii
    n_io = n_ix - n_ii
    return (n_ii, n_oi, n_io, n_xx - n_ii - n_oi - n_io)


def raw_freq(n_ii, n_ix, n_xi, n_xx):
    """Scores bigrams by their frequency"""
    return float(n_ii) / n_xx


class MILikeScorer(BigramAssociationMeasureI):
    def __init__(self, power=3):
        self.power = power

    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        """Scores bigrams using a variant of mutual information"""
        return n_ii ** self.power / float(n_ix * n_xi)

mi_like = MILikeScorer()


def pmi(n_ii, n_ix, n_xi, n_xx):
    """Scores bigrams by pointwise mutual information"""
    return _ln(n_ii * n_xx) - _ln(n_ix * n_xi)


def phi_sq(n_ii, n_ix, n_xi, n_xx):
    """Scores bigrams using phi-square, the square of the Pearson correlation
    coefficient.
    """
    n_ii, n_io, n_oi, n_oo = _contingency(n_ii, n_ix, n_xi, n_xx)

    return (float((n_ii*n_oo - n_io*n_oi)**2) /
            ((n_ii + n_io) * (n_ii + n_oi) * (n_io + n_oo) * (n_oi + n_oo)))


def chi_sq(n_ii, n_ix, n_xi, n_xx):
    """Scores bigrams using chi-square, i.e. phi-sq multiplied by the number
    of bigrams.
    """
    return n_xx * phi_sq(n_ii, n_ix, n_xi, n_xx)


def student_t(n_ii, n_ix, n_xi, n_xx):
    """Scores bigrams using Student's t test with independence hypothesis
    for unigrams.
    """
    return (n_ii - float(n_ix*n_xi) / n_xx) / (n_ii + _SMOOTHING) ** .5


def dice(n_ii, n_ix, n_xi, n_xx):
    """Scores bigrams using Dice's coefficient."""
    return 2 * float(n_ii) / (n_ix + n_xi)


def jaccard(BigramAssociationMeasureI):
    """Scores bigrams using the Jaccard index (= dice / (2*dice))."""
    n_ii, n_io, n_oi, n_oo = _contingency(n_ii, n_ix, n_xi, n_xx)
    return float(n_ii) / (n_ii + n_io + n_oi)
                   

