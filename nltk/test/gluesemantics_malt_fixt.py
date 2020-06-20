# -*- coding: utf-8 -*-


def setup_module(module):
    from nose import SkipTest
    from nltk.parse.malt import MaltParser

    try:
        depparser = MaltParser("maltparser-1.7.2")
    except LookupError as e:
        raise SkipTest("MaltParser is not available") from e
