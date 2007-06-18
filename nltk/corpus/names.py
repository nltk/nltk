# Natural Language Toolkit: Names Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Names Corpus, Version 1.3 (1994-03-29)
Copyright (C) 1991 Mark Kantrowitz
Additions by Bill Ross

This corpus contains 5001 female names and 2943 male names, sorted
alphabetically, one per line.
(Used in NLTK with permission.  See the README file for details.)
"""       

from util import *
import os

documents = {
    'female':     'Female names',
    'male':       'Male names'
    }

def read_document(name, as_objects=False):
    filename = find_corpus_file('names', name, '.txt')
    return StreamBackedCorpusView(filename, names_tokenizer)
read = read_document

def names_tokenizer(stream):
    return [stream.readline().strip()]

def demo():
    from nltk.corpora import names
    from random import shuffle
    from pprint import pprint

    print "20 female names"
    female = list(read('female'))
    shuffle(female)
    pprint(female[:20])

    print "20 male names"
    male = list(read('male'))
    shuffle(male)
    pprint(male[:20])

if __name__ == '__main__':
    demo()

