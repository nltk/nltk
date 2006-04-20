# Natural Language Toolkit: PP Attachment Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read lines from the Prepositional Phrase Attachment Corpus.

The PP Attachment Corpus contains several files having the format:

  sentence_id verb noun1 preposition noun2 attachment

E.g.:

  42960 gives authority to administration V
  46742 gives inventors of microchip N

The PP attachment is to the verb phrase (V) or noun phrase (N), i.e.:

  (VP gives (NP authority) (PP to administration))
  (VP gives (NP inventors (PP of microchip)))

The corpus contains the following files:

training:   training set
devset:     development test set, used for algorithm development.
test:       test set, used to report results
bitstrings: word classes derived from Mutual Information
            Clustering for the Wall Street Journal.

Ratnaparkhi, Adwait (1994). A Maximum Entropy Model for Prepositional
Phrase Attachment.  Proceedings of the ARPA Human Language Technology
Conference.  [http://www.cis.upenn.edu/~adwait/papers/hlt94.ps]

The PP Attachment Corpus is distributed with NLTK with the permission
of the author.
"""       

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
from nltk_lite.tag import string2tags, string2words
import os

items = ['training', 'devset', 'test']

item_name = {
    'training': 'training set',
    'devset': 'development test set',
    'test': 'test set'
    }

def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "ppattach", file)
        for line in open(path).readlines():
            yield tuple(line.split())

def dictionary(files = items):
    for t in raw(files):
        yield {
            'sent': t[0],
            'verb': t[1],
            'noun1': t[2],
            'prep': t[3],
            'noun2': t[4],
            'attachment': t[5]
            }

def demo():
    from nltk_lite.corpora import ppattach
    from itertools import islice
    from pprint import pprint

    pprint(list(islice(ppattach.raw('training'), 0, 5)))
    pprint(list(islice(ppattach.dictionary('training'), 0, 5)))

if __name__ == '__main__':
    demo()

