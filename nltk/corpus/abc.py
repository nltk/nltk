# Natural Language Toolkit: ABC Text Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Australian Broadcasting Commission 2006
http://www.abc.net.au/

Contents:
* Rural News    http://www.abc.net.au/rural/news/
* Science News  http://www.abc.net.au/science/news/
"""       

from util import *
from nltk import tokenize
import os, re

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
  'rural':           'Rural News',
  'science':         'Science News',
}

#: A list of all documents in this corpus.
items = list(documents)

def read_document(name, format='tokenized'):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
    """
    filename = find_corpus_file('abc', name, '.txt')
    if format == 'raw':
        return open(filename).read()
    elif format == 'tokenized':
        return StreamBackedCorpusView(filename, read_wordpunc_block)
    else:
        raise ValueError('Bad format: expected raw or tokenized')

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(name):
    """@Return the given document as a single string."""
    return read_document(name, 'raw')

def tokenized(name):
    """@Return the given document as a list of words and punctuation
    symbols.
    @rtype: C{list} of C{str}"""
    return read_document(name, 'tokenized')

######################################################################
#{ Demo
######################################################################
def demo():
    from ntlk.corpus import 
    rural = read('rural')
    for word in rural[20:100]:
        print word,

if __name__ == '__main__':
    demo()
