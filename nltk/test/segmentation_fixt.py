# -*- coding: utf-8 -*-
from __future__ import absolute_import


# skip segmentation.doctest if numpy is not available
def setup_module(module):
    from nose import SkipTest

    try:
        import numpy
    except ImportError:
        raise SkipTest("segmentation.doctest requires numpy")
