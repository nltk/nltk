# -*- coding: utf-8 -*-


def setup_module(module):
    from nose import SkipTest

    try:
        import gensim
    except ImportError:
        raise SkipTest("Gensim doctest requires gensim")
