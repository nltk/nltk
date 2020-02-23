# -*- coding: utf-8 -*-


def teardown_module(module=None):
    from nltk.corpus import wordnet

    wordnet._unload()
