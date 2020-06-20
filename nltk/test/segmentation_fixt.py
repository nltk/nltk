# -*- coding: utf-8 -*-


# skip segmentation.doctest if numpy is not available
def setup_module(module):
    from nose import SkipTest

    try:
        import numpy
    except ImportError as e:
        raise SkipTest("segmentation.doctest requires numpy") from e
