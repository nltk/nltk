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

items = [
  'rural',
  'science',
]    

item_name = {
  'rural':           'Rural News',
  'science':         'Science News',
}

def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "abc", file + ".txt")
        f = open(path)
        preamble = True
        for line in f.readlines():
            for t in tokenize.wordpunct(line):
                yield t

def demo():
    from nltk.corpora import abc
    from itertools import islice

    for word in islice(abc.raw('science'), 0, 100):
        print word,

if __name__ == '__main__':
    demo()
