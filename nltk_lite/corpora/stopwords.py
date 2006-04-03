# Natural Language Toolkit: Stopwords Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the Stopwords Corpus.
"""       

from nltk_lite.corpora import get_basedir
import os

items = ['danish', 'dutch', 'english', 'french', 'german', 'italian',
         'norwegian', 'portuguese', 'russian', 'spanish', 'swedish']

item_name = {
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

def raw(files = 'english'):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "stopwords", file)
        for word in open(path).readlines():
            yield word.strip()

def demo():
    from nltk_lite.corpora import stopwords
    from itertools import islice
    from pprint import pprint

    print "20 English stopwords"
    pprint(list(islice(stopwords.raw(), 0, 20)))

    print "20 Danish stopwords"
    pprint(list(islice(stopwords.raw('danish'), 0, 20)))

if __name__ == '__main__':
    demo()

