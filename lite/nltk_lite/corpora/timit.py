# Natural Language Toolkit: TIMIT Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Haejoong Lee <haejoong@ldc.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the NLTK TIMIT Corpus.

TIMIT Corpus  --  http://.../

This corpus contains selected texts from the TIMIT corpus

* ...
"""       

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
from itertools import islice
import os, re

__all__ = ["speakers", "items", "raw", "phonetic", "dictionary"]

PREFIX = os.path.join(get_basedir(),"timit")

speakers = []
items = []
dictionary = {}

for f in os.listdir(PREFIX):
    if re.match("^dr[0-9]-[a-z]{4}[0-9]$", f):
        speakers.append(f)
        for g in os.listdir(os.path.join(PREFIX,f)):
            if g.endswith(".txt"):
                items.append(f+':'+g[:-4])
speakers.sort()
items.sort()

# read dictionary
for l in open(os.path.join(PREFIX,"timitdic.txt")):
    if l[0] == ';': continue
    a = l.strip().split('  ')
    dictionary[a[0]] = a[1].strip('/').split()


def _prim(ext, sentences=items, offset=False):
    for sent in sentences:
        fnam = os.path.sep.join([PREFIX] + sent.split(':')) + ext
        for l in open(fnam):
            if not l.strip(): continue
            a = l.split()
            if offset:
                yield (a[2],int(a[0]),int(a[1]))
            else:
                yield a[2]


def raw(sentences=items, offset=False):
    return _prim(".wrd", sentences, offset)

    
def phonetic(sentences=items, offset=False):
    return _prim(".phn", sentences, offset)


def demo():
    from nltk_lite.corpora import timit
    from itertools import islice

    for x in timit.phonetic(sentences=items[:1]):
        print x
    print dictionary['again']


if __name__ == '__main__':
    demo()
