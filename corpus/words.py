# Natural Language Toolkit: Wordlist Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the Wordlist Corpus.
"""       

from util import *
import os

lexicons = {'en': 'English Wordlist'}
items = list(lexicons)

def read_lexicon(name='en'):
    filename = find_corpus_file('words', name)
    return open(filename).read().split()
read = read_lexicon

def demo():
    from nltk.corpus import words
    from itertools import islice
    from pprint import pprint

    pprint(words.read()[0:20])

if __name__ == '__main__':
    demo()

