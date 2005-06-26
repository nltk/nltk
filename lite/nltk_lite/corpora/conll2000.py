# Natural Language Toolkit: CONLL Corpus Reader
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read chunk structures from the CONLL Corpus
"""       

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
from nltk_lite.parse import tree
import os

items = ['train', 'test']

item_name = {
    'train': 'training set',
    'test':  'test set'
    }

def _list_sent(sent):
    return [tokenize.whitespace(line) for line in tokenize.line(sent)]

def raw(files = items):
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2000", file + ".txt")
        s = open(path).read()
        for sent in tokenize.blankline(s):
            yield [word for (word, tag, chunk) in _list_sent(sent)]

def tagged(files = items):
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2000", file + ".txt")
        s = open(path).read()
        for sent in tokenize.blankline(s):
            yield [(word, tag) for (word, tag, chunk) in _list_sent(sent)]

def chunked(files = items, chunk_types=('NP',)):
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2000", file + ".txt")
        s = open(path).read()
        for sent in tokenize.blankline(s):
            yield tree.conll_chunk(sent, chunk_types)

def demo():
    from nltk_lite.corpora import conll2000
    from itertools import islice

    print "CONLL Chunked data\n"
    
    print "Raw text:"
    for sent in islice(conll2000.raw(), 0, 5):
        print sent
    print

    print "Tagged text:"
    for sent in islice(conll2000.tagged(), 0, 5):
        print sent
    print

    print "Chunked text:"
    for tree in islice(conll2000.chunked(chunk_types=('NP', 'PP', 'VP')), 0, 5):
        print tree.pp()
    print


if __name__ == '__main__':
    demo()

