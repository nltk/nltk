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

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
import os, re

items = [
  'overheard',
  'wine',
  'pirates',
  'singles'
]    

item_name = {
  'overheard':           'Overheard in New York',
  'wine':                'Fine Wine Diary',
  'pirates':             "Pirates of the Carribean: Dead Man's Chest",
  'singles':             'Singles ads',
}

def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "webtext", file)
        f = open(path)
        preamble = True
        for line in f.readlines():
            for t in tokenize.wordpunct(line):
                yield t

def demo():
    from nltk_lite.corpora import webtext
    from itertools import islice

    for word in islice(webtext.raw('wine'), 0, 100):
        print word,

if __name__ == '__main__':
    demo()
