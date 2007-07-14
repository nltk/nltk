# Natural Language Toolkit: Web Text Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the Web Text Corpus

This is a collection of diverse, contemporary text genres,
collected by scraping publicly accessible archives of web postings.
This data is disseminated in preference to publishing URLs for
individuals to download and clean up (the usual model for web corpora).

overheard: Overheard in New York (partly censored) http://www.overheardinnewyork.com/ (2006)
wine:  Fine Wine Diary http://www.finewinediary.com/ (2005-06)
pirates: Movie script from Pirates of the Caribbean: Dead Man's Chest http://www.imsdb.com/  (2006)
singles: Singles ads  http://search.classifieds.news.com.au/

"""       

from util import *
from nltk import tokenize
import os, re

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
  'overheard':           'Overheard in New York',
  'wine':                'Fine Wine Diary',
  'pirates':             "Pirates of the Carribean: Dead Man's Chest",
  'singles':             'Singles ads',
}

#: A list of all documents in this corpus.
items = sorted(documents)

def read_document(item=items, format='tokenized'):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
    """
    if isinstance(item, list):
        return concat([read(doc, format) for doc in item])
    filename = find_corpus_file('webtext', item)
    if format == 'raw':
        return open(filename).read()
    elif format == 'tokenized':
        return StreamBackedCorpusView(filename, read_wordpunct_block)
    else:
        raise ValueError('Bad format: expected raw or tokenized')

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(item=items):
    """@return: the given document as a single string."""
    return read_document(item, 'raw')

def tokenized(item=items):
    """@return: the given document as a list of words and punctuation
    symbols.
    @rtype: C{list} of C{str}"""
    return read_document(item, 'tokenized')

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import webtext
    for word in webtext.read('wine')[0:100]:
        print word,

if __name__ == '__main__':
    demo()
