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

#: A dictionary specifying the list of lexicons defined by this
#: corpus.  The keys of this dictionary are the lexicon names;
#: and the values are plaintext descriptions.
lexicons = {'en': 'English Wordlist'}

#: A list of all lexicons in this corpus.
items = sorted(lexicons)

def read_lexicon(item='en', format='listed'):
    """
    Read the given lexicon from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'listed'}: a list of words
    """
    filename = find_corpus_file('words', item)
    if format == 'raw':
        return open(filename).read()
    elif format == 'listed':
        return open(filename).read().split()
    else:
        raise ValueError('Expected format to be raw or listed')

######################################################################
#{ Convenience Functions
######################################################################
read = read_lexicon

def raw(name):
    """@return: the given document as a single string."""
    return read_document(name, 'raw')

def listed(name):
    """@return: the given document as a list"""
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

