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
items = sorted(documents)

def read_document(item, format='chunked', chunk_types=('NP','VP','PP')):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
      - C{'tagged'}: a list of tagged words
      - C{'chunked'}: a chunk tree containing tagged words

    @param chunk_types: If C{format='chunked'}, then C{chunk_types}
        determines which chunk types will be included.  Any chunks
        not listed in the chunk_types list will have their words
        listed at the top level.  For example, to list the document
        with only noun phrase chunks marked, use ('NP',).
    """
    filename = find_corpus_file('conll2002', item)
    if format == 'raw': return open(filename).read()
    return Conll2000CorpusView(filename, format, chunk_types)

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(item):
    """Return the given document as a single string"""
    return read_document(item, format='raw')

def tokenized(item):
    """Return the given document as a list of words and punctuation
    symbols."""
    return read_document(item, format='tokenized')

def tagged(item):
    """Return the given document as a list of (word, part-of-speech)
    tuples."""
    return read_document(item, format='tagged')

def chunked(item, chunk_types=('NP','VP','PP')):
    """Return the given document as a chunk tree, containing tagged
    words."""
    return read_document(item, format='chunked', chunk_types=chunk_types)

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import conll2002

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

