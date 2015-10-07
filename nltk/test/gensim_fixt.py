# -*- coding: utf-8 -*-
from __future__ import absolute_import

def setup_module(module):
    from nose import SkipTest
    try:
        import gensim
    except ImportError:
        raise SkipTest("classify.doctest requires numpy")