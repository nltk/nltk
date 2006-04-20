# Natural Language Toolkit: Wordlist Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the Wordlist Corpus.
"""       

from nltk_lite.corpora import get_basedir
import os

items = ['en']

item_name = {
    'en': 'English Wordlist',
    }

def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "words", file)
        for word in open(path).readlines():
            yield word.strip()

def demo():
    from nltk_lite.corpora import words
    from itertools import islice
    from pprint import pprint

    pprint(list(islice(words.raw(), 0, 20)))

if __name__ == '__main__':
    demo()

