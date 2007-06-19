# Natural Language Toolkit: Indian Language POS-Tagged Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Indian Language POS-Tagged Corpus
Collected by A Kumaran, Microsoft Research, India
Distributed with permission

Contents:
- Bangla: IIT Kharagpur
- Hindi: Microsoft Research India
- Marathi: IIT Bombay
- Telugu: IIIT Hyderabad
"""       

from util import *
from nltk import tokenize
from nltk.tag import string2tags, string2words
import os

documents = ['bangla', 'hindi', 'marathi', 'telugu']

def read_document(name, format='tagged'):
    """
    @param format: raw or tagged.
    """
    filename = find_corpus_file('indian', name, '.pos')
    if format == 'raw':
        return StreamBackedCorpusView(filename, tokenize_indian_raw)
    elif format == 'tagged':
        return StreamBackedCorpusView(filename, tokenize_indian_tagged)
    else:
        raise ValueError('format should be "raw" or "tagged"')
read = read_document

def tokenize_indian_raw(stream):
    line = stream.readline()
    if line.startswith('<'): return []
    else: return [string2words(line, sep='_')]

def tokenize_indian_tagged(stream):
    line = stream.readline()
    if line.startswith('<'): return []
    else: return [string2tags(line, sep='_')]

def sample(language):
    from nltk.corpus import indian
    from nltk import extract
    print language.capitalize() + ":"
    for word, tag in indian.read(language, 'tagged')[8]:
        print word + "/" + `tag`,
    print

def demo():

    sample('bangla')
    sample('hindi')
    sample('marathi')
    sample('telugu')

if __name__ == '__main__':
    demo()
