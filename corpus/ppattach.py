# Natural Language Toolkit: PP Attachment Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read lines from the Prepositional Phrase Attachment Corpus.

The PP Attachment Corpus contains several files having the format:

sentence_id verb noun1 preposition noun2 attachment

For example:

42960 gives authority to administration V
46742 gives inventors of microchip N

The PP attachment is to the verb phrase (V) or noun phrase (N), i.e.:

(VP gives (NP authority) (PP to administration))
(VP gives (NP inventors (PP of microchip)))

The corpus contains the following files:

training:   training set
devset:     development test set, used for algorithm development.
test:       test set, used to report results
bitstrings: word classes derived from Mutual Information Clustering for the Wall Street Journal.

Ratnaparkhi, Adwait (1994). A Maximum Entropy Model for Prepositional
Phrase Attachment.  Proceedings of the ARPA Human Language Technology
Conference.  [http://www.cis.upenn.edu/~adwait/papers/hlt94.ps]

The PP Attachment Corpus is distributed with NLTK with the permission
of the author.
"""       

from util import *
from nltk import tokenize
from nltk.tag import string2tags, string2words
import os

documents = {
    'training': 'training set',
    'devset': 'development test set',
    'test': 'test set'
    }

class PPAttachment:
    def __init__(self, sent, verb, noun1, prep, noun2, attachment):
        self.sent = sent
        self.verb = verb
        self.noun1 = noun1
        self.prep = prep
        self.noun2 = noun2
        self.attachment = attachment

    def __repr__(self):
        return ('PPAttachment(sent=%r, verb=%r, noun1=%r, prep=%r, '
                'noun2=%r, attachment=%r)' %
                (self.sent, self.verb, self.noun1, self.prep,
                 self.noun2, self.attachment))

def read_document(name, as_objects=False):
    filename = find_corpus_file('ppattach', name)
    if as_objects:
        return StreamBackedCorpusView(filename, ppattach_object_tokenizer)
    else:
        return StreamBackedCorpusView(filename, ppattach_tuple_tokenizer)
read = read_document

def ppattach_tuple_tokenizer(stream):
    line = stream.readline()
    if line:
        return [tuple(line.split())]
    else:
        return []

def ppattach_object_tokenizer(stream):
    line = stream.readline()
    if line:
        return [PPAttachment(*line.split())]
    else:
        return []

def demo():
    from nltk.corpora import ppattach
    from pprint import pprint

    pprint(read('training')[0:5])
    pprint(read('training', as_objects=True)[0:5])

if __name__ == '__main__':
    demo()

