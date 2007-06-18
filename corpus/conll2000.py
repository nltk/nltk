# Natural Language Toolkit: CONLL Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read chunk structures from the CONLL-2000 Corpus
"""       

from util import *
from nltk import tokenize, chunk, tree
import os

documents = {
    'train': 'training set',
    'test':  'test set'
    }

class Conll2000CorpusView(StreamBackedCorpusView):
    def __init__(self, corpus_file, format, chunk_types):
        self.format = format
        self.chunk_types = chunk_types
        StreamBackedCorpusView.__init__(self, corpus_file)
        
    def tokenize_block(self, stream):
        # Read the next sentence.
        sent = tokenize_blankline(stream)[0].strip()
        # If format is chunked, use the conllstr2tree function to parse it.
        if self.format == 'chunked':
            return [chunk.conllstr2tree(sent, self.chunk_types)]

        # Otherwise, split the string into lines and select out either the
        # word&tag (tagged) or just the word (raw) from each line.
        lines = [line.split() for line in sent.split('\n')
                 if line != '-DOCSTART- -DOCSTART- O']
        if self.format == 'tagged':
            return [[(word, tag) for (word, tag, chunk_typ) in lines]]
        elif self.format == 'raw':
            return [[word for (word, tag, chunk_typ) in lines]]

def read_document(name, format='chunked', chunk_types=('NP','VP','PP')):
    filename = find_corpus_file('conll2000', name, '.txt')
    return Conll2000CorpusView(filename, format, chunk_types)
read = read_document

def demo():
    print "CONLL Chunked data\n"
    
    print "Raw text:"
    for sent in read('train', 'raw')[0:5]:
        print sent
    print

    print "Tagged text:"
    for sent in read('train', 'tagged')[0:5]:
        print sent
    print

    print "Chunked text:"
    for tree in read('train', 'chunked', chunk_types=('NP', 'PP'))[0:5]:
        print tree
    print


if __name__ == '__main__':
    demo()

