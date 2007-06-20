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

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
    'bangla': 'IIT Kharagpur',
    'hindi': 'Microsoft Research India',
    'marathi': 'IIT Bombay',
    'telugu': 'IIIT Hyderabad',
    }

#: A list of all documents in this corpus.
items = list(documents)

def read_document(name, format='tagged'):
    """
    @param format: raw or tokenized or tagged.
    """
    filename = find_corpus_file('indian', name, '.pos')
    if format == 'raw':
        return(open(filename).read())
    if format == 'tokenized':
        return StreamBackedCorpusView(filename, read_tokenized_indian_block)
    elif format == 'tagged':
        return StreamBackedCorpusView(filename, read_tagged_indian_block)
    else:
        raise ValueError('format should be "raw" or "tokenized" or "tagged"')
read = read_document

def read_tokenized_indian_block(stream):
    line = stream.readline()
    if line.startswith('<'): return []
    else: return [string2words(line, sep='_')]

def read_tagged_indian_block(stream):
    line = stream.readline()
    if line.startswith('<'): return []
    else: return [string2tags(line, sep='_')]

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(name):
    """@Return the given document as a single string."""
    return read_document(name, 'raw')

def tokenized(name):
    """@Return the given document as a list of words and punctuation
    symbols.
    @rtype: C{list} of C{str}"""
    return read_document(name, 'tokenized')

def tagged(name):
    """@Return the given document as a list of sentences, where each
    sentence is a list of tagged words.  Tagged words are encoded as
    tuples of (word, part-of-speech)."""
    return read_document(name)

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import indian
    from nltk import extract
    
    def sample(language):
        print language.capitalize() + ":"
        for word, tag in indian.read(language, 'tagged')[8]:
            print word + "/" + `tag`,
        print

    sample('bangla')
    sample('hindi')
    sample('marathi')
    sample('telugu')

if __name__ == '__main__':
    demo()
