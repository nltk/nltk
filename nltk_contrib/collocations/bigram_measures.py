# Natural Language Toolkit: Bigram Association Measures
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
"""
TODO: write comment
"""

import math as _math


class BigramAssociationMeasureI(object):
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        raise AssertionError, "This is an interface"


_ln = lambda x: _math.log(x, 2.0)


def _contingency(n_ii, n_ix, n_xi, n_xx):
    n_io = n_ix - n_ii
    n_oi = n_xi - n_ii
    return (n_ii, n_io, n_oi, n_xx - n_ii - n_io - n_oi)


def raw_freq(n_ii, n_ix, n_xi, n_xx):
    return float(n_ii) / n_xx


class MILikeScorer(BigramAssociationMeasureI):
    def __init__(self, power=3):
        self.power = power

    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        return n_ii ** self.power / float(n_ix * n_xi)

mi_like = MILikeScorer()


def pmi(n_ii, n_ix, n_xi, n_xx):
    return _ln(n_ii * n_xx) - _ln(n_ix * n_xi)


def phi_sq(n_ii, n_ix, n_xi, n_xx):
    n_ii, n_io, n_oi, n_oo = _contingency(n_ii, n_ix, n_xi, n_xx)

    return (float((n_ii*n_oo - n_io*n_oi)**2) /
            ((n_ii + n_io) * (n_ii + n_oi) * (n_io + n_oo) * (n_oi + n_oo)))


def chi_sq(n_ii, n_ix, n_xi, n_xx):
    return n_xx * phi_sq(n_ii, n_ix, n_xi, n_xx)


def student_t(n_ii, n_ix, n_xi, n_xx):
    return (n_ii - float(n_ix*n_xi)/n_xx) / (n_ii +.000001) ** .5


def dice(n_ii, n_ix, n_xi, n_xx):
    return 2 * float(n_ix) / (n_ix + n_xi)


def jaccard(BigramAssociationMeasureI):
    n_ii, n_io, n_oi, n_oo = _contingency(n_ii, n_ix, n_xi, n_xx)
    return float(n_ii) / (n_ii + n_io + n_oi)  # = dice/(2*dice)
                   

