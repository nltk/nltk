# Natural Language Toolkit: Brown Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the Brown Corpus.

Brown Corpus: A Standard Corpus of Present-Day Edited American
English, for use with Digital Computers, by W. N. Francis and
H. Kucera (1964), Department of Linguistics, Brown University,
Providence, Rhode Island, USA.  Revised 1971, Revised and
Amplified 1979.  Distributed with NLTK with the permission of the
copyright holder.  Source: http://www.hit.uib.no/icame/brown/bcm.html

The Brown Corpus is divided into the following files:

a. press: reportage
b. press: editorial
c. press: reviews
d. religion
e. skill and hobbies
f. popular lore
g. belles-lettres
h. miscellaneous: government & house organs
j. learned
k: fiction: general
l: fiction: mystery
m: fiction: science
n: fiction: adventure
p. fiction: romance
r. humor
"""       

from util import *
from nltk import tokenize
from nltk.tag import string2tags, string2words
import os

documents = {
    'a': 'press: reportage',
    'b': 'press: editorial',
    'c': 'press: reviews',
    'd': 'religion',
    'e': 'skill and hobbies',
    'f': 'popular lore',
    'g': 'belles-lettres',
    'h': 'government',
    'j': 'learned',
    'k': 'fiction: general',
    'l': 'fiction: mystery',
    'm': 'fiction: science',
    'n': 'fiction: adventure',
    'p': 'fiction: romance',
    'r': 'humor'
    }

class BrownCorpusView(StreamBackedCorpusView):
    def __init__(self, corpus_file, tagged, grouped_by_sent, grouped_by_para):
        self.tagged = tagged
        self.grouped_by_sent = grouped_by_sent
        self.grouped_by_para = grouped_by_para
        StreamBackedCorpusView.__init__(self, corpus_file)
        
    def tokenize_block(self, stream):
        """Reads one paragraph at a time."""
        para = []
        while True:
            line = stream.readline().strip()
            if line:
                if self.tagged:
                    words = string2tags(line)
                else:
                    words = string2words(line)
                if self.grouped_by_sent:
                    para.append(words)
                else:
                    para.extend(words)
            elif para:
                if self.grouped_by_para:
                    return [para]
                else:
                    return para
            else:
                return []

def read_document(name, tagged=True, grouped_by_sent=True,
                  grouped_by_para = False):
    filename = find_corpus_file('brown', name)
    return BrownCorpusView(filename, tagged, grouped_by_sent, grouped_by_para)

read = read_document

def demo():
    d1 = read('a')
    for sent in d1[3:5]:
        print 'Sentence from a:', sent

    d2 = read('b', grouped_by_sent=False)
    print 'Words from b:', d2[220:240]
                       
    d3 = read('c', grouped_by_sent=False, tagged=False)
    print 'Untagged words from c:', d3[220:240]
                       
if __name__ == '__main__':
    demo()

