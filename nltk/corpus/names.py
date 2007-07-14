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

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
    'female':     'Female names',
    'male':       'Male names'
    }

#: A list of all documents in this corpus.
items = sorted(documents)

def read_document(item=items, format='listed'):
    """
    Return the given list of names.  C{item} can be 'female' or
    'male', or the filename of a file containing a name list.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'listed'}: a list of names
    """
    if isinstance(item, list):
        return concat([read(doc, format) for doc in item])
    filename = find_corpus_file('names', item, '.txt')
    if format == 'listed':
        return StreamBackedCorpusView(filename, read_names_block)
    elif format == 'raw':
        return open(filename).read()
    else:
        raise ValueError('Expected format to be listed or raw')

def read_names_block(stream):
    return [stream.readline().strip()]

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(item=items):
    """@return: the given document as a single string."""
    return read_document(item, 'raw')

def listed(item=items):
    """@return: the given document as a list"""
    return read_document(item, 'listed')

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import names
    from random import shuffle
    from pprint import pprint

    print "20 female names"
    female = list(names.read('female'))
    shuffle(female)
    pprint(female[:20])

    print "20 male names"
    male = list(names.read('male'))
    shuffle(male)
    pprint(male[:20])

if __name__ == '__main__':
    demo()



