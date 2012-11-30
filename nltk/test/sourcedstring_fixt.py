# -*- coding: utf-8 -*-
from __future__ import absolute_import
from nltk.compat import PY3

def setup_module(module):
    from nose import SkipTest
    if PY3:
        raise SkipTest("sourcedstring.doctest causes too many failures under Python 3.x")