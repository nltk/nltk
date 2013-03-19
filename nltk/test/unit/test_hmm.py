# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from nltk import hmm

def test_forward_probability():
    import numpy as np
    from numpy.testing import assert_array_almost_equal
    model, states, symbols = hmm._market_hmm_example()

    # example from p. 385, Huang et al
    seq = [('up', None), ('up', None)]
    expected = np.array([
        [0.09, 0.02, 0.35],
        [0.0357, 0.0085, 0.1792]
    ], np.float64)

    log_prob_matrix = model._forward_probability(seq)
    prob_matrix = 2**log_prob_matrix

    assert_array_almost_equal(prob_matrix, expected)



def setup_module(module):
    from nose import SkipTest
    try:
        import numpy
    except ImportError:
        raise SkipTest("numpy is required for nltk.test.test_hmm")
