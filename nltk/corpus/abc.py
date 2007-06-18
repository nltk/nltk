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

documents = {
  'rural':           'Rural News',
  'science':         'Science News',
}

def read_document(name):
    filename = find_corpus_file('abc', name, '.txt')
    return StreamBackedCorpusView(filename, tokenize_wordpunct)
read = read_document

def demo():
    rural = read('rural')
    for word in rural[20:100]:
        print word,

if __name__ == '__main__':
    demo()
