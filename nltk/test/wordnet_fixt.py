# -*- coding: utf-8 -*-
from __future__ import absolute_import


def setup_module(module):
    from nose import SkipTest

    raise SkipTest("Wordnet tests take too much time...")


def teardown_module(module=None):
    from nltk.corpus import wordnet
    wordnet._unload()
