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
items = sorted(lexicons)

def read_lexicon(item='en', format='listed'):
    filename = find_corpus_file('words', item)
    if format == 'raw':
        return open(filename).read()
    elif format == 'listed':
        return open(filename).read().split()
    else:
        raise ValueError('Expected format to be raw or listed')
read = read_lexicon

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(name):
    """@Return the given document as a single string."""
    return read_document(name, 'raw')

def listed(name):
    """@Return the given document as a list"""
    return read_document(name, 'listed')

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import words
    from pprint import pprint

    pprint(words.read()[0:20])

if __name__ == '__main__':
    demo()

