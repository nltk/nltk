# -*- coding: utf-8 -*-
from __future__ import absolute_import


# probability.doctest uses HMM which requires numpy;
# skip probability.doctest if numpy is not available

def setup_module(module):
    from nose import SkipTest
    try:
        import numpy
    except ImportError:
        raise SkipTest("probability.doctest requires numpy")
