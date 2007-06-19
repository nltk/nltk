# Natural Language Toolkit: Stopwords Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the Stopwords Corpus.
"""       

from util import *
import os

lexicons = {
    'danish':     'Danish stopwords',
    'dutch':      'Dutch stopwords',
    'english':    'English stopwords',
    'french':     'French stopwords',
    'german':     'German stopwords',
    'italian':    'Italian stopwords',
    'norwegian':  'Norwegian stopwords',
    'portuguese': 'Portuguese stopwords',
    'russian':    'Russian stopwords',
    'spanish':    'Spanish stopwords',
    'swedish':    'Swedish stopwords',
    }
items = list(lexicons)

def read_lexicon(name='english'):
    filename = find_corpus_file('stopwords', name)
    return open(filename).read().split()
read = read_lexicon

def demo():
    from nltk.corpus import stopwords
    from itertools import islice
    from pprint import pprint

    print "20 English stopwords"
    pprint(stopwords.read()[300:320])

    print "20 Danish stopwords"
    pprint(stopwords.read('danish')[10:30])

if __name__ == '__main__':
    demo()

