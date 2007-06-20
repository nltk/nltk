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
from nltk import chunk, tree
import os

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
    'train': 'training set',
    'test':  'test set'
    }

#: A list of all documents in this corpus.
items = sorted(documents)

class Conll2000CorpusView(StreamBackedCorpusView):
    def __init__(self, corpus_file, format, chunk_types):
        if format not in ('chunked', 'tokenized', 'tagged'):
            raise ValueError('Expected format to be chunked, tokenized, '
                             'or tagged.')
        self.format = format
        self.chunk_types = chunk_types
        StreamBackedCorpusView.__init__(self, corpus_file)
        
    def read_block(self, stream):
        # Read the next sentence.
        sent = read_blankline_block(stream)[0].strip()
        # If format is chunked, use the conllstr2tree function to parse it.
        if self.format == 'chunked':
            return [chunk.conllstr2tree(sent, self.chunk_types)]

        # Otherwise, split the string into lines and select out either the
        # word&tag (tagged) or just the word (raw) from each line.
        lines = [line.split() for line in sent.split('\n')
                 if line != '-DOCSTART- -DOCSTART- O']
        if self.format == 'tagged':
            return [[(word, tag) for (word, tag, chunk_typ) in lines]]
        elif self.format == 'tokenized':
            return [[word for (word, tag, chunk_typ) in lines]]

def read_document(item, format='chunked', chunk_types=('NP','VP','PP')):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
      - C{'tagged'}: a list of tagged words
      - C{'chunked'}: a chunk tree containing tagged words
    """
    filename = find_corpus_file('conll2000', item, '.txt')
    if format == 'raw': return open(filename).read()
    return Conll2000CorpusView(filename, format, chunk_types)

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(item):
    return read_document(item, format='raw')

def tokenized(item):
    return read_document(item, format='tokenized')

def tagged(item):
    return read_document(item, format='tagged')

def chunked(item, chunk_types=('NP','VP','PP')):
    return read_document(item, format='chunked', chunk_types=chunk_types)

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import conll2000
    print "CONLL Chunked data\n"
    
    print "Raw text:"
    for sent in conll2000.read('train', 'raw')[0:5]:
        print sent
    print

    print "Tagged text:"
    for sent in conll2000.read('train', 'tagged')[0:5]:
        print sent
    print

    print "Chunked text:"
    for tree in conll2000.read('train', 'chunked',
                               chunk_types=('NP', 'PP'))[0:5]:
        print tree
    print


if __name__ == '__main__':
    demo()

