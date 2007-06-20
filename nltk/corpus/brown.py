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
from nltk.tag import string2tags, string2words
import os

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
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

#: A list of all documents in this corpus.
items = sorted(documents)

class BrownCorpusView(StreamBackedCorpusView):
    def __init__(self, corpus_file, tagged, grouped_by_sent, grouped_by_para):
        self.tagged = tagged
        self.grouped_by_sent = grouped_by_sent
        self.grouped_by_para = grouped_by_para
        StreamBackedCorpusView.__init__(self, corpus_file)
        
    def read_block(self, stream):
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

def read_document(item, format='tagged', grouped_by_sent=True,
                  grouped_by_para = False):
    """
    Read and return the given document C{item}.
    @param format: tagged, tokenized, or raw.
    @param grouped_by_sent: If true, then the result will contain one
        list for each sentence.  
    @param grouped_by_para: If true, then the result will contain one
        list for each paragraph.  If C{grouped_by_sent} is also true,
        then each of these paragraphs will contain a list of sentences.
    """
    filename = find_corpus_file('brown', item)
    if format == 'raw':
        return open(filename).read()
    elif format not in ('tagged', 'tokenized'):
        raise ValueError('Expected format to be raw, tagged, or tokenized')
    return BrownCorpusView(filename, format==tagged,
                           grouped_by_sent, grouped_by_para)

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def tagged(item, grouped_by_sent=True, grouped_by_para=False):
    """@Return the given document as a list of sentences, where each
    sentence is a list of tagged words.  Tagged words are encoded as
    tuples of (word, part-of-speech)."""
    return read_document(item, 'tagged', grouped_by_sent, grouped_by_para)

def tokenized(item, grouped_by_sent=True, grouped_by_para=False):
    """@Return the given document as a list of sentences, where each
    sentence is a list of words."""
    return read_document(item, 'tokenized', grouped_by_sent, grouped_by_para)

def raw(item):
    """@Return the given document as a single string."""
    return read_document(item, format='raw')

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import brown
    
    d1 = brown.read('a')
    for sent in d1[3:5]:
        print 'Sentence from a:', sent

    d2 = brown.read('b', grouped_by_sent=False)
    print 'Words from b:', d2[220:240]
                       
    d3 = brown.read('c', grouped_by_sent=False, tagged=False)
    print 'Untagged words from c:', d3[220:240]
                       
if __name__ == '__main__':
    demo()

