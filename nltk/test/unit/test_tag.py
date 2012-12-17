# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

def test_basic():
    from nltk.tag import pos_tag
    from nltk.tokenize import word_tokenize

    result = pos_tag(word_tokenize("John's big idea isn't all that bad."))
    assert result == [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'),
                      ('idea', 'NN'), ('is', 'VBZ'), ("n't", 'RB'),
                      ('all', 'DT'), ('that', 'DT'), ('bad', 'JJ'),
                      ('.', '.')]


def setup_module(module):
    from nose import SkipTest
    try:
        import numpy
    except ImportError:
        raise SkipTest("numpy is required for nltk.test.test_tag")
