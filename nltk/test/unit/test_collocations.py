# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from nltk.collocations import BigramCollocationFinder

def test_bigram2():

    sent = 'this this is is a a test test'.split()

    b = BigramCollocationFinder.from_words(sent)
    assert b.ngram_fd.items() == \
        [(('a', 'a'), 1), (('a', 'test'), 1), (('is', 'a'), 1), (('is', 'is'), 1), (('test', 'test'), 1), (('this', 'is'), 1), (('this', 'this'), 1)]
    assert b.word_fd.items() == \
        [('a', 2), ('is', 2), ('test', 2), ('this', 2)]
    assert len(sent) == sum(b.word_fd.values()) == sum(b.ngram_fd.values()) + 1

def test_bigram3():

    sent = 'this this is is a a test test'.split()

    b = BigramCollocationFinder.from_words(sent,window_size=3)
    assert b.ngram_fd.items() == \
        [(('a', 'test'), 3), (('is', 'a'), 3), (('this', 'is'), 3), (('a', 'a'), 1), (('is', 'is'), 1), (('test', 'test'), 1), (('this', 'this'), 1)]
    assert b.word_fd.items() == \
        [('a', 2), ('is', 2), ('test', 2), ('this', 2)]
    assert len(sent) == sum(b.word_fd.values()) == (sum(b.ngram_fd.values()) + 2 + 1) / 2.0

def test_bigram5():

    sent = 'this this is is a a test test'.split()

    b = BigramCollocationFinder.from_words(sent,window_size=5)
    assert b.ngram_fd.items() == \
        [(('a', 'test'), 4), (('is', 'a'), 4), (('this', 'is'), 4), (('is', 'test'), 3), (('this', 'a'), 3), (('a', 'a'), 1), (('is', 'is'), 1), (('test', 'test'), 1), (('this', 'this'), 1)]
    assert b.word_fd.items() == \
        [('a', 2), ('is', 2), ('test', 2), ('this', 2)]
    assert len(sent) == sum(b.word_fd.values()) == (sum(b.ngram_fd.values()) + 4 + 3 + 2 + 1) / 4.0

