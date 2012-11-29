# -*- coding: utf-8 -*-
from __future__ import absolute_import
from nltk.compat import PY3

def setup_module():
    from nose import SkipTest
    if PY3:
        raise SkipTest("parse.doctest is temporarily disabled "
                       "under Python 3.x because there are bugs "
                       "causing an infinite loop.")