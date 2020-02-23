# -*- coding: utf-8 -*-
from nltk.compat import PY3


def setup_module(module):
    from nose import SkipTest

    if PY3:
        raise SkipTest("compat.doctest is for Python 2.x")
