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
from nltk import chunk
from nltk import tree
from conll2000 import Conll2000CorpusView
import os

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
    'ned.train': 'Dutch training set',
    'ned.testa': 'Dutch test set a',
    'ned.testb': 'Dutch test set b',
    'esp.train': 'Spanish training set',
    'esp.testa': 'Spanish test set a',
    'ned.testb': 'Spanish test set b',
    }

#: A list of all documents in this corpus.
items = list(documents)

def read_document(name, format='chunked', chunk_types=('NP','VP','PP')):
    filename = find_corpus_file('conll2002', name)
    return Conll2000CorpusView(filename, format, chunk_types)

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(name):
    return read_document(name, format='raw')

def tokenized(name):
    return read_document(name, format='tokenized')

def tagged(name):
    return read_document(name, format='tagged')

def chunked(name, chunk_types=('NP','VP','PP')):
    return read_document(name, format='chunked', chunk_types=chunk_types)

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpora import conll2002

    print "CONLL2002 NE data\n"
    
    print "Raw text -- Dutch:"
    for sent in conll2002.read('ned.train', 'raw')[0:5]:
        print sent
    print
    
    print "Raw text --Spanish:"
    for sent in conll2002.read('esp.train', 'raw')[0:5]:
        print sent
    print

    print "POS Tagged text -- Dutch:"
    for sent in conll2002.read('ned.train', 'tagged')[0:5]:
        print sent
    print
    
    print "POS Tagged text --Spanish:"
    for sent in conll2002.read('esp.train', 'tagged')[0:5]:
        print sent
    print

    print "Named Entity chunked text -- Dutch:"
    for tree in conll2002.read('ned.train', 'chunked')[0:5]:
        print tree
    print
    
    print "Named Entity chunked text --Spanish:"
    for tree in conll2002.read('esp.train', 'chunked')[0:5]:
        print tree
    print


if __name__ == '__main__':
    demo()

