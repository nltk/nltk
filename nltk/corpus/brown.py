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
    """
    A specialized corpus view for brown documents.  It can be customized
    via flags to divide brown corpus documents up by sentence or paragraph,
    and to include or omit part of speech tags.  C{BrownCorpusView}
    objects are typically created by L{read_document()} (not directly by
    the brown corpus modules' users).
    """
    def __init__(self, corpus_file, tagged, group_by_sent, group_by_para):
        self.tagged = tagged
        self.group_by_sent = group_by_sent
        self.group_by_para = group_by_para
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
                if self.group_by_sent:
                    para.append(words)
                else:
                    para.extend(words)
            elif para:
                if self.group_by_para:
                    return [para]
                else:
                    return para
            else:
                return []

def read_document(item, format='tagged', group_by_sent=True, group_by_para = False):
    """
    Read and return the given document.

    @param item: The item name of the document to return.
    
    @param format: Determines the format that the result will be
    returned in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
      - C{'tagged'}: a list of (word, part-of-speech) tuples.
      
    @param group_by_sent: If true, then the result will contain one
        list for each sentence.
        
    @param group_by_para: If true, then the result will contain one
        list for each paragraph.  If C{group_by_sent} is also true,
        then each of these paragraphs will contain a list of sentences.
    """
    if isinstance(item, list):
        return concat([read_document(doc, format, group_by_sent,
                                     group_by_para) for doc in item])
    filename = find_corpus_file('brown', item)
    if format == 'raw':
        return open(filename).read()
    elif format not in ('tagged', 'tokenized'):
        raise ValueError('Expected format to be raw, tagged, or tokenized')
    return BrownCorpusView(filename, format=='tagged', group_by_sent, group_by_para)

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def tagged(item=items, group_by_sent=True, group_by_para=False):
    """
    @return the given document as a list of sentences, where each
    sentence is a list of tagged words.  Tagged words are encoded as
    tuples of (word, part-of-speech).
    @param group_by_sent, group_by_para: Controls whether the
        result groups words by sentence or paragraph, or both or neither.
        By default, words are grouped by sentence.
    """
    return read_document(item, 'tagged', group_by_sent, group_by_para)

def tokenized(item=items, group_by_sent=True, group_by_para=False):
    """
    @return the given document as a list of sentences, where each
    sentence is a list of words.
    @param group_by_sent, group_by_para: Controls whether the
        result groups words by sentence or paragraph, or both or neither.
        By default, words are grouped by sentence.
    """
    return read_document(item, 'tokenized', group_by_sent, group_by_para)

def raw(item=items):
    """
    @return the given document as a single string.
    @param group_by_sent, group_by_para: Controls whether the
        result groups words by sentence or paragraph, or both or neither.
        By default, words are grouped by sentence.
    """
    return read_document(item, format='raw')

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import brown
    
    d1 = brown.read('a')
    for sent in d1[3:5]:
        print 'Sentence from a:', sent

    d2 = brown.read('b', group_by_sent=False)
    print 'Words from b:', d2[220:240]
                       
    d3 = brown.read('c', group_by_sent=False, format='tokenized')
    print 'Untagged words from c:', d3[220:240]

if __name__ == '__main__':
    demo()

