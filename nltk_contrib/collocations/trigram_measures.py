# Natural Language Toolkit: Trigram Association Measures
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
_ln = lambda x: _math.log(x, 2.0)


class TrigramAssociationMeasureI(object):
    def __call__(self, n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
        raise AssertionError, "This is an interface"


def raw_freq(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    return float(n_iii) / n_xxx


def pmi(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    return _ln(n_ixx * n_xix * nxxi) - 2*_ln(n_xxx)


