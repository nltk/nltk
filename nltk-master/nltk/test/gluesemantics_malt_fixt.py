# -*- coding: utf-8 -*-
from __future__ import absolute_import

def setup_module(module):
    from nose import SkipTest
    from nltk.parse.malt import MaltParser

    try:
        depparser = MaltParser()
    except LookupError:
        raise SkipTest("MaltParser is not available")
