# -*- coding: utf-8 -*-
from nltk.corpus import teardown_module


def setup_module(module):
    from nose import SkipTest

    raise SkipTest(
        "portuguese_en.doctest imports nltk.examples.pt which doesn't exist!"
    )
