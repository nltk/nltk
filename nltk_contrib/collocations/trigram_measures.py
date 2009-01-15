# Natural Language Toolkit: Trigram Association Measures
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#

# FIXME: docstring not current
"""
A number of functions to score trigram associations. Each association measure
is provided as a function with eight arguments:
    trigram_score_fn(n_iii, (n_iix, n_ixi, n_xii), (n_ixx, n_xix, n_xxi), n_xxx)
Each argument counts the occurrences of a particular event in a corpus. The
letter i in the suffix refers to the appearance of the word in question, while
x indicates to the appearance of any word. Thus, for example:
n_iii counts (w1, w2, w3), i.e. the trigram being scored
n_ixx counts (w1, *, *)
n_xxx counts (*, *, *), i.e. any trigram
"""

import math as _math
_log = lambda x: _math.log(x, 2.0)

_SMALL = 1e-20


class TrigramAssociationMeasureI(object):
    """Interface for a trigram association measure function"""
    def __call__(self, n_iii,
             (n_iix, n_ixi, n_xii),
             (n_ixx, n_xix, n_xxi),
             n_xxx):
        raise AssertionError, "This is an interface"


def _contingency(n_iii,
             (n_iix, n_ixi, n_xii),
             (n_ixx, n_xix, n_xxi),
             n_xxx):
    """Calculates values of a trigram contingency table (or cube) from marginal
    values.
    """
    n_oii = n_xii - n_iii
    n_ioi = n_ixi - n_iii
    n_iio = n_iix - n_iii
    n_ooi = n_xxi - n_iii - n_oii - n_ioi
    n_oio = n_xix - n_iii - n_oii - n_iio
    n_ioo = n_ixx - n_iii - n_ioi - n_iio
    n_ooo = n_xxx - n_iii - n_oii - n_ioi - n_iio - n_ooi - n_oio - n_ioo

    return (n_iii, n_oii, n_ioi, n_ooi,
            n_iio, n_oio, n_ioo, n_ooo)


def _expected_values(cont):
    """Calculates expected values for a contingency table."""
    n_xxx = sum(cont)
    # For each contingency table cell
    for i in range(8):
        yield ((cont[i] + cont[i ^ 1]) *
               (cont[i] + cont[i ^ 2]) *
               (cont[i] + cont[i ^ 4]) /
               float(n_xxx ** 2))


def raw_freq(n_iii,
             (n_iix, n_ixi, n_xii),
             (n_ixx, n_xix, n_xxi),
             n_xxx):
    """Scores trigrams by their frequency"""
    return float(n_iii) / n_xxx


class MILikeScorer(TrigramAssociationMeasureI):
    def __init__(self, power=3):
        self.power = power

    def __call__(self, n_iii,
             (n_iix, n_ixi, n_xii),
             (n_ixx, n_xix, n_xxi),
             n_xxx):
        """Scores trigrams using a variant of mutual information"""
        return n_iii ** self.power / float(n_ixx * n_xix * n_xxi)

mi_like = MILikeScorer()


def pmi(n_iii,
             (n_iix, n_ixi, n_xii),
             (n_ixx, n_xix, n_xxi),
             n_xxx):
    """Scores trigrams by pointwise mutual information, as in Manning and
    Schutze 5.4.
    """
    return _log(n_iii * n_xxx * n_xxx) - _log(n_ixx * n_xix * n_xxi)


def student_t(n_iii,
             (n_iix, n_ixi, n_xii),
             (n_ixx, n_xix, n_xxi),
             n_xxx):
    """Scores trigrams using Student's t test with independence hypothesis
    for unigrams, as in Manning and Schutze 5.3.2.
    """
    return ((n_iii - (n_ixx * n_xix * n_xxi) / (n_xxx * n_xxx)) /
            (n_iii + _SMALL) ** .5)


def chi_sq(*marginals):
    """Scores trigrams using Pearson's chi-square as in Manning and Schutze
    5.3.3.
    """
    cont = _contingency(*marginals)
    exps = _expected_values(cont)
    return sum((obs - exp) ** 2 / (exp + _SMALL)
               for obs, exp in zip(cont, exps))


def likelihood_ratio(*marginals):
    """Scores trigrams using likelihood ratios as in Manning and Schutze 5.3.4.
    """
    cont = _contingency(*marginals)
    # Although probably obvious, I don't understand why this negation is needed
    return -2 * sum(obs * _log(float(obs) / (exp + _SMALL) + _SMALL)
                   for obs, exp in zip(cont, _expected_values(cont)))


def poisson_stirling(n_iii,
             (n_iix, n_ixi, n_xii),
             (n_ixx, n_xix, n_xxi),
             n_xxx):
    """Scores trigrams using the Poisson-Stirling measure."""
    exp = n_ixx * n_xix * n_xxi / float(n_xxx * n_xxx)
    return n_iii * (_log(n_iii / exp) - 1)


def tmi(*marginals):
    """Scores bigrams using True Mutual Information."""
    cont = _contingency(*marginals)
    exps = _expected_values(cont)
    n_xxx = float(marginals[-1])
    # Although probably obvious, I don't understand why this negation is needed
    return -sum(obs / n_xxx * _log(float(obs) / (exp + _SMALL) + _SMALL)
               for obs, exp in zip(cont, exps))


def jaccard(*marginals):
    """Scores trigrams using the Jaccard index."""
    cont = _contingency(*marginals)
    return float(cont[0]) / sum(cont[:-1])
