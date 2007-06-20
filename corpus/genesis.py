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
import os

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
    'english-kjv': 'Genesis, King James version (Project Gutenberg)',
    'english-web': 'Genesis, World English Bible (Project Gutenberg)',
    'french': 'Genesis, Louis Segond 1910',
    'german': 'Genesis, Luther Translation',
    'swedish': 'Genesis, Gamla och Nya Testamentet, 1917 (Project Runeberg)',
    'finnish': 'Genesis, Suomen evankelis-luterilaisen kirkon kirkolliskokouksen vuonna 1992 kayttoon ottama suomennos'
}

#: A list of all documents in this corpus.
items = list(documents)

def read_document(name='english-kjv', format='tokenized'):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
    """
    filename = find_corpus_file('genesis', name, '.txt')
    if format == 'raw':
        return open(filename).read()
    elif format == 'tokenized':
        return StreamBackedCorpusView(filename, read_wordpunct_block)
    else:
        raise ValueError('Bad format: expected raw or tokenized')

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

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import genesis

    print 'English:'
    for word in genesis.read('english-kjv')[:27]:
        print word,
    print

    print 'Finnish:'
    for word in genesis.read('finnish')[:27]:
        print word,
    print

if __name__ == '__main__':
    demo()

