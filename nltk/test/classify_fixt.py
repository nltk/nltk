# -*- coding: utf-8 -*-


# most of classify.doctest requires numpy
def setup_module(module):
    from nose import SkipTest

    try:
        import numpy
    except ImportError as e:
        raise SkipTest("classify.doctest requires numpy") from e
