# Natural Language Toolkit: Gutenberg Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
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

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
import os, re

items = [
  'austen-emma',
  'austen-persuasion',
  'austen-sense',
  'bible-kjv',
  'blake-poems',
  'blake-songs',
  'chesterton-ball',
  'chesterton-brown',
  'chesterton-thursday',
  'milton-paradise',
  'shakespeare-caesar',
  'shakespeare-hamlet',
  'shakespeare-macbeth',
  'whitman-leaves'
]    

item_name = {
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


def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "gutenberg", file + ".txt")
        f = open(path)
        preamble = True
        for line in f.readlines():
            if not preamble:
                for t in tokenize.wordpunct(line):
                    yield t
            if line[:5] == '*END*':
                preamble = False

def demo():
    from nltk_lite.corpora import gutenberg
    from itertools import islice

    for word in islice(gutenberg.raw('bible-kjv'), 0, 100):
        print word,

if __name__ == '__main__':
    demo()
