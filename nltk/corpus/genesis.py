# Natural Language Toolkit: Genesis Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
The Genesis Corpus.

This corpus has been prepared from several web sources; formatting,
markup and verse numbers have been stripped.

english-kjv - Genesis, King James version (Project Gutenberg)
english-web - Genesis, World English Bible (Project Gutenberg)
french - Genesis, Louis Segond 1910
german - Genesis, Luther Translation
swedish - Genesis, Gamla och Nya Testamentet, 1917 (Project Runeberg)
finnish - Genesis, Suomen evankelis-luterilaisen kirkon kirkolliskokouksen vuonna 1992 kayttoon ottama suomennos
"""

from util import *
from nltk import tokenize
import os

documents = {
    'english-kjv': 'Genesis, King James version (Project Gutenberg)',
    'english-web': 'Genesis, World English Bible (Project Gutenberg)',
    'french': 'Genesis, Louis Segond 1910',
    'german': 'Genesis, Luther Translation',
    'swedish': 'Genesis, Gamla och Nya Testamentet, 1917 (Project Runeberg)',
    'finnish': 'Genesis, Suomen evankelis-luterilaisen kirkon kirkolliskokouksen vuonna 1992 kayttoon ottama suomennos'
}

def read_document(name='english-kjv'):
    filename = find_corpus_file('genesis', name, '.txt')
    return StreamBackedCorpusView(filename, tokenize_wordpunct)
read = read_document

def demo():
    from nltk.corpora import genesis
    from itertools import islice

    print 'English:'
    for word in read('english-kjv')[:27]:
        print word,
    print

    print 'Finnish:'
    for word in read('finnish')[:27]:
        print word,
    print

if __name__ == '__main__':
    demo()

