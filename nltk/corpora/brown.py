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

items = list('abcdefghjklmnpr')

item_name = {
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

def _read(files, conversion_function):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "brown", file)
        f = open_corpus(path)
        for sent in tokenize.line(f.read()):
            if sent:
                yield conversion_function(sent)

def raw(files = items):
    """Read text from the Brown Corpus."""
    return _read(files, string2words)

def tagged(files = items):
    """Read tagged text from the Brown Corpus."""
    return _read(files, string2tags)

def demo():
    from nltk.corpora import brown
    from itertools import islice
    from pprint import pprint

    pprint(list(islice(brown.raw('a'), 0, 5)))

    pprint(list(islice(brown.tagged('a'), 0, 5)))

if __name__ == '__main__':
    demo()

