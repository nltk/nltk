# Natural Language Toolkit: CONLL 2002 Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#              Edward Loper <edloper@gradient.cis.upenn.edu>
#              Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read Named Entity tagged data as chunk structures from the CONLL-2002 Corpus
"""       

from util import *
from nltk import tokenize, chunk
from nltk import tree
import os

esp = ['esp.train', 'esp.testa', 'esp.testb']	
ned = ['ned.train', 'ned.testa', 'ned.testb']
items = esp + ned

item_name = {
    'ned.train': 'Dutch training set',
    'ned.testa': 'Dutch test set a',
    'ned.testb': 'Dutch test set b',
    'esp.train': 'Spanish training set',
    'esp.testa': 'Spanish test set a',
    'ned.testb': 'Spanish test set b',
    }

def _list_sent(sent):
    return [tokenize.whitespace(line) for line in tokenize.line(sent)]

def raw(files = ['ned.train', 'esp.train']):
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2002", file)
        f = open_corpus(path)
        s = f.read()
        # remove initial -DOCSTART- -DOCSTART- O
        if s.startswith('-DOCSTART'):
            s = s[23:]
        for sent in tokenize.blankline(s):
            yield [word for (word, tag, ner) in _list_sent(sent)]

def pos_tagged(files = ['ned.train', 'esp.train']):
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2002", file)
        f = open_corpus(path)
        s = f.read()
        # remove initial -DOCSTART- -DOCSTART- O
        if s.startswith('-DOCSTART-'):
            s = s[23:]
        for sent in tokenize.blankline(s):
            yield [(word, tag) for (word, tag, ner) in _list_sent(sent)]

def ne_chunked(files = ['ned.train', 'esp.train'], chunk_types=('LOC','ORG','PER')):
    """
    MISC has been omitted
    """
    if type(files) is str: files = (files,)
    for file in files:
        path = os.path.join(get_basedir(), "conll2002", file)
        f = open_corpus(path)
        s = f.read()
        # remove initial -DOCSTART- -DOCSTART- O
        if s.startswith('-DOCSTART'):
            s = s[23:]
        for sent in tokenize.blankline(s):
            yield chunk.conllstr2tree(sent, chunk_types)

def demo():
    from nltk.corpora import conll2002
    from itertools import islice

    print "CONLL2002 NE data\n"
    
    print "Raw text -- Dutch:"
    for sent in islice(conll2002.raw(files = ['ned.train']), 0, 5):
        print sent
    print
    
    print "Raw text --Spanish:"
    for sent in islice(conll2002.raw(files = ['esp.train']), 0, 5):
        print sent
    print

    print "POS Tagged text -- Dutch:"
    for sent in islice(conll2002.pos_tagged(files = ['ned.train']), 0, 5):
        print sent
    print
    
    print "POS Tagged text --Spanish:"
    for sent in islice(conll2002.pos_tagged(files = ['esp.train']), 0, 5):
        print sent
    print

    print "Named Entity chunked text -- Dutch:"
    for tree in islice(conll2002.ne_chunked(files = ['ned.train']), 0, 5):
        print tree
    print
    
    print "Named Entity chunked text --Spanish:"
    for tree in islice(conll2002.ne_chunked(files = ['esp.train']), 0, 5):
        print tree
    print


if __name__ == '__main__':
    demo()

