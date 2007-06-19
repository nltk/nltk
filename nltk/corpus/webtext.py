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

documents = {
  'overheard':           'Overheard in New York',
  'wine':                'Fine Wine Diary',
  'pirates':             "Pirates of the Carribean: Dead Man's Chest",
  'singles':             'Singles ads',
}

def read_document(name):
    filename = find_corpus_file('webtext', name)
    return StreamBackedCorpusView(filename, tokenize_wordpunct)
read = read_document

def demo():
    from nltk.corpus import webtext
    from itertools import islice

    for word in webtext.read('wine')[0:100]:
        print word,

if __name__ == '__main__':
    demo()
