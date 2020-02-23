# -*- coding: utf-8 -*-


# most of classify.doctest requires numpy
def setup_module(module):
    from nose import SkipTest

    try:
        import numpy
    except ImportError:
        raise SkipTest("classify.doctest requires numpy")
