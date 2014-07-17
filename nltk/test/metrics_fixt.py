# -*- coding: utf-8 -*-
from __future__ import absolute_import


def setup_module(module):
    from nose import SkipTest

    try:
        import scipy
    except ImportError:
        raise SkipTest('SciPy is not found.')
