# Natural Language Toolkit: Gutenberg Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the NLTK Gutenberg Corpus.

Project Gutenberg  --  http://gutenberg.net/

This corpus contains selected texts from Project Gutenberg:

* Jane Austen (3)
* William Blake (2)
* G. K. Chesterton (3)
* King James Bible
* John Milton
* William Shakespeare (3)
* Walt Whitman
"""       

from util import *
from nltk import tokenize
import os, re

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {
  'austen-emma':         'Jane Austen: Emma',
  'austen-persuasion':   'Jane Austen: Persuasion',
  'austen-sense':        'Jane Austen: Sense and Sensibility',
  'bible-kjv':           'King James Bible',
  'blake-poems':         'William Blake: Poems',
  'blake-songs':         'Willian Blake: Songs of Innocence and Experience',
  'chesterton-ball':     'G.K. Chesterton: The Ball and The Cross',
  'chesterton-brown':    'G.K. Chesterton: The Wisdom of Father Brown',
  'chesterton-thursday': 'G.K. Chesterton: The Man Who Was Thursday',
  'milton-paradise':     'John Milton: Paradise Lost',
  'shakespeare-caesar':  'William Shakespeare: Julius Caesar',
  'shakespeare-hamlet':  'William Shakespeare: Hamlet',
  'shakespeare-macbeth': 'William Shakespeare: Macbeth',
  'whitman-leaves':      'Walt Whitman: Leaves of Grass',
}

#: A list of all documents in this corpus.
items = list(documents)

class GutenbergCorpusView(StreamBackedCorpusView):
    """
    Version of StreamBackedCorpusView that skips the Gutenberg preamble
    section; and then uses the wordpunct tokenizer.
    """
    def __init__(self, corpus_file):
        StreamBackedCorpusView.__init__(self, corpus_file)
        self._skipped_preamble = False

    def read_block(self, stream):
        # Skip the preamble.
        if not self._skipped_preamble:
            while True:
                line = stream.readline()
                if line.rstrip()[:5] == '*END*':
                    self._skipped_preamble = True
                    break
                elif line == '':
                    break
        # Then tokenize using wordpunct.
        return tokenize_wordpunct(stream)

def read_document(name='english-kjv', format='tokenized'):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
    """
    filename = find_corpus_file('gutenberg', name, '.txt')
    if format == 'raw':
        return open(filename).read()
    elif format == 'tokenized':
        return GutenbergCorpusView(filename)
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
    from nltk.corpus import gutenberg

    for word in gutenberg.read('bible-kjv')[0:100]:
        print word,

if __name__ == '__main__':
    demo()
