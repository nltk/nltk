# Natural Language Toolkit: Brown Corpus Reader
#
# Copyright (C) 2001-2005 University of Pennsylvania
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

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
from nltk_lite.tag import string2tags, string2words
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
    'h': 'miscellaneous: government & house organs',
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
        f = open(path).read()
        for sent in tokenize.blankline(f):
            yield conversion_function(sent)

def raw(files = items):
    return _read(files, string2words)

def tagged(files = items):
    return _read(files, string2tags)

def demo():
    from nltk_lite.corpora import brown
    from itertools import islice

    for sent in islice(brown.raw('a'), 0, 5):
        print sent

    for sent in islice(brown.tagged('a'), 0, 5):
        print sent

if __name__ == '__main__':
    demo()

