# -*- coding: utf-8 -*-
from __future__ import absolute_import


def setup_module(module):
    from nose import SkipTest
    from nltk.inference.mace import Mace

    try:
        m = Mace()
        m._find_binary('mace4')
    except LookupError:
        raise SkipTest(
            "Mace4/Prover9 is not available so inference.doctest was skipped"
        )
