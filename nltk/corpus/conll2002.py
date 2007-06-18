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
from conll2000 import Conll2000CorpusView
import os

documents = {
    'ned.train': 'Dutch training set',
    'ned.testa': 'Dutch test set a',
    'ned.testb': 'Dutch test set b',
    'esp.train': 'Spanish training set',
    'esp.testa': 'Spanish test set a',
    'ned.testb': 'Spanish test set b',
    }

def read_document(name, format='chunked', chunk_types=('NP','VP','PP')):
    filename = find_corpus_file('conll2002', name)
    return Conll2000CorpusView(filename, format, chunk_types)
read = read_document

def demo():
    from nltk.corpora import conll2002
    from itertools import islice

    print "CONLL2002 NE data\n"
    
    print "Raw text -- Dutch:"
    for sent in read('ned.train', 'raw')[0:5]:
        print sent
    print
    
    print "Raw text --Spanish:"
    for sent in read('esp.train', 'raw')[0:5]:
        print sent
    print

    print "POS Tagged text -- Dutch:"
    for sent in read('ned.train', 'tagged')[0:5]:
        print sent
    print
    
    print "POS Tagged text --Spanish:"
    for sent in read('esp.train', 'tagged')[0:5]:
        print sent
    print

    print "Named Entity chunked text -- Dutch:"
    for tree in read('ned.train', 'chunked')[0:5]:
        print tree
    print
    
    print "Named Entity chunked text --Spanish:"
    for tree in read('esp.train', 'chunked')[0:5]:
        print tree
    print


if __name__ == '__main__':
    demo()

