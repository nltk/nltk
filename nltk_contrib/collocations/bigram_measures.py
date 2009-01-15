# Natural Language Toolkit: Bigram Association Measures
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
# FIXME: docstring not current
"""
A number of functions to score bigram associations. Each association measure
is provided as a function with four arguments:
    bigram_score_fn(n_ii, (n_ix, n_xi), n_xx)
Each argument counts the occurrences of a particular event in a corpus. The
letter i in the suffix refers to the appearance of the word in question, while
x indicates to the appearance of any word. Thus:
n_ii counts (w1, w2), i.e. the bigram being scored
n_ix counts (w1, *)
n_xi counts (*, w2)
n_xx counts (*, *), i.e. any bigram
"""

import math as _math
_log = lambda x: _math.log(x, 2.0)

_SMALL = 1e-20


class BigramAssociationMeasureI(object):
    """Interface for a bigram association measure function"""
    def __call__(self, n_ii, (n_ix, n_xi), n_xx):
        raise AssertionError, "This is an interface"


def _contingency(n_ii, (n_ix, n_xi), n_xx):
    """Calculates values of a bigram contingency table from marginal values."""
    n_oi = n_xi - n_ii
    n_io = n_ix - n_ii
    return (n_ii, n_oi, n_io, n_xx - n_ii - n_oi - n_io)


def _expected_values(cont):
    """Calculates expected values for a contingency table."""
    n_xx = sum(cont)
    # For each contingency table cell
    for i in range(4):
        yield (cont[i] + cont[i ^ 1]) * (cont[i] + cont[i ^ 2]) / float(n_xx)


def raw_freq(n_ii, (n_ix, n_xi), n_xx):
    """Scores bigrams by their frequency"""
    return float(n_ii) / n_xx


class MILikeScorer(BigramAssociationMeasureI):
    def __init__(self, power=3):
        self.power = power

    def __call__(self, n_ii, (n_ix, n_xi), n_xx):
        """Scores bigrams using a variant of mutual information"""
        return n_ii ** self.power / float(n_ix * n_xi)

mi_like = MILikeScorer()


def pmi(n_ii, (n_ix, n_xi), n_xx):
    """Scores bigrams by pointwise mutual information, as in Manning and
    Schutze 5.4.
    """
    return _log(n_ii * n_xx) - _log(n_ix * n_xi)


def phi_sq(*marginals):
    """Scores bigrams using phi-square, the square of the Pearson correlation
    coefficient.
    """
    n_ii, n_io, n_oi, n_oo = _contingency(*marginals)

    return (float((n_ii*n_oo - n_io*n_oi)**2) /
            ((n_ii + n_io) * (n_ii + n_oi) * (n_io + n_oo) * (n_oi + n_oo)))


def chi_sq(n_ii, (n_ix, n_xi), n_xx):
    """Scores bigrams using chi-square, i.e. phi-sq multiplied by the number
    of bigrams, as in Manning and Schutze 5.3.3.
    """
    return n_xx * phi_sq(n_ii, (n_ix, n_xi), n_xx)


def student_t(n_ii, (n_ix, n_xi), n_xx):
    """Scores bigrams using Student's t test with independence hypothesis
    for unigrams, as in Manning and Schutze 5.3.2.
    """
    return (n_ii - float(n_ix*n_xi) / n_xx) / (n_ii + _SMALL) ** .5


def dice(n_ii, (n_ix, n_xi), n_xx):
    """Scores bigrams using Dice's coefficient."""
    return 2 * float(n_ii) / (n_ix + n_xi)


def jaccard(*marginals):
    """Scores bigrams using the Jaccard index (= dice / (2*dice))."""
    n_ii, n_io, n_oi, n_oo = _contingency(*marginals)
    return float(n_ii) / (n_ii + n_io + n_oi)
                   

def _likelihood(k, n, x):
    """Binomial log-likelihood function"""
    if x == 1.0:
        x -= _SMALL
    elif x == 0.0:
        x += _SMALL
    return k * _log(x) + (n - k) * _log(1 - x)

    
def likelihood_ratio(n_ii, (n_ix, n_xi), n_xx):
    """Scores bigrams using likelihood ratios as in Manning and Schutze 5.3.4.
    """
    p = float(n_xi) / n_xx
    p1 = float(n_ii) / n_ix
    p2 = float(n_xi - n_ii) / (n_xx - n_ix)
    return -2 * (
            _likelihood(n_ii, n_ix, p) +
            _likelihood(n_xi - n_ii, n_xx - n_ix, p) -
            _likelihood(n_ii, n_ix, p1) -
            _likelihood(n_xi - n_ii, n_xx - n_ix, p2))


# An alternative implementation: which do we keep?
def likelihood_ratio(*marginals):
    """Scores bigrams using likelihood ratios as in Manning and Schutze 5.3.4.
    """
    cont = _contingency(*marginals)
    return 2 * sum(obs * _log(float(obs) / exp + _SMALL)
                   for obs, exp in zip(cont, _expected_values(cont)))


def poisson_stirling(n_ii, (n_ix, n_xi), n_xx):
    """Scores bigrams using the Poisson-Stirling measure."""
    exp = n_ix * n_xi / float(n_xx)
    return n_ii * (_log(n_ii / exp) - 1)


def tmi(*marginals):
    """Scores bigrams using True Mutual Information."""
    cont = _contingency(*marginals)
    exps = _expected_values(cont)
    n_xx = float(marginals[-1])
    return sum(obs / n_xx * _log(float(obs) / (exp + _SMALL) + _SMALL)
               for obs, exp in zip(cont, exps))
