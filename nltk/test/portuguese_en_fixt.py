# -*- coding: utf-8 -*-
from __future__ import absolute_import
from nltk.compat import PY3

from nltk.corpus import teardown_module


def setup_module(module):
    from nose import SkipTest

    raise SkipTest(
        "portuguese_en.doctest imports nltk.examples.pt which doesn't exist!"
    )

    if not PY3:
        raise SkipTest(
            "portuguese_en.doctest was skipped because non-ascii doctests are not supported under Python 2.x"
        )
