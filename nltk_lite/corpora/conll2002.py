# Natural Language Toolkit: CONLL 2002 Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#              Edward Loper <edloper@gradient.cis.upenn.edu>
#              Ewan Klein <ewan@iinf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read Named Entity tagged data as chunk structures from the CONLL-2002 Corpus
"""       

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize, chunk
from nltk_lite.parse import tree
import os

items = ['ned.train', 'ned.testa', 'ned.testb']

item_name = {
    'ned.train': 'Dutch training set',
    'ned.testa':  'Dutch test set a',
    'ned.testb':  'Dutch test set b'
    }

def _list_sent(sent):
    return [tokenize.whitespace(line) for line in tokenize.line(sent)]

def raw(files = ['ned.train']):
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2002", file)
        s = open(path).read()
        # remove initial -DOCSTART- -DOCSTART- O
        s = s[23:]
        for sent in tokenize.blankline(s):
            yield [word for (word, tag, ner) in _list_sent(sent)]

def pos_tagged(files = ['ned.train']):
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2002", file)
        s = open(path).read()
        # remove initial -DOCSTART- -DOCSTART- O
        s = s[23:]
        for sent in tokenize.blankline(s):
            yield [(word, tag) for (word, tag, ner) in _list_sent(sent)]

def ne_chunked(files = ['ned.train'], chunk_types=('LOC','ORG','PER')):
    """
    MISC has been omitted
    """
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2002", file)
        s = open(path).read()
        # remove initial -DOCSTART- -DOCSTART- O
        s = s[23:]
        for sent in tokenize.blankline(s):
            yield chunk.conllstr2tree(sent, chunk_types)

def demo():
    from nltk_lite.corpora import conll2002
    from itertools import islice

    print "CONLL Chunked data\n"
    
    print "Raw text:"
    for sent in islice(conll2002.raw(), 0, 5):
        print sent
    print

    print "POS Tagged text:"
    for sent in islice(conll2002.pos_tagged(), 0, 5):
        print sent
    print

    print "Named Entity Chunked  text:"
    for tree in islice(conll2002.ne_chunked(), 0, 5):
        print tree.pp()
    print


if __name__ == '__main__':
    demo()

