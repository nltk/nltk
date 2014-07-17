# -*- coding: utf-8 -*-
from __future__ import absolute_import


# most of classify.doctest requires numpy
def setup_module(module):
    from nose import SkipTest
    try:
        import numpy
        from sklearn.svm import SVC
    except ImportError:
        raise SkipTest("classify.doctest requires numpy and sklearn.svm.SVC")
