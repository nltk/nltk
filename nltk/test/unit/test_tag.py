# -*- coding: utf-8 -*-


def test_basic():
    from nltk.tag import pos_tag
    from nltk.tokenize import word_tokenize

    result = pos_tag(word_tokenize("John's big idea isn't all that bad."))
    assert result == [
        ('John', 'NNP'),
        ("'s", 'POS'),
        ('big', 'JJ'),
        ('idea', 'NN'),
        ('is', 'VBZ'),
        ("n't", 'RB'),
        ('all', 'PDT'),
        ('that', 'DT'),
        ('bad', 'JJ'),
        ('.', '.'),
    ]


def setup_module(module):
    from nose import SkipTest

    try:
        import numpy
    except ImportError as e:
        raise SkipTest("numpy is required for nltk.test.test_tag") from e
