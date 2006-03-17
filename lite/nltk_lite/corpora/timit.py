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

__all__ = ["items", "raw", "phonetic", "speakers", "dictionary", "spkrinfo"]

PREFIX = os.path.join(get_basedir(),"timit")

speakers = []
items = []
dictionary = {}
spkrinfo = {}

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

# read spkrinfo
for l in open(os.path.join(PREFIX,"spkrinfo.txt")):
    if l[0] == ';': continue
    rec = l[:54].split() + [l[54:].strip()]
    key = "dr%s-%s%s" % (rec[2],rec[1].lower(),rec[0].lower())
    spkrinfo[key] = rec
    
def _prim(ext, sentences=items, offset=False):
    for sent in sentences:
        fnam = os.path.sep.join([PREFIX] + sent.split(':')) + ext
        r = []
        for l in open(fnam):
            if not l.strip(): continue
            a = l.split()
            if offset:
                r.append((a[2],int(a[0]),int(a[1])))
            else:
                r.append(a[2])
        yield r

def raw(sentences=items, offset=False):
    return _prim(".wrd", sentences, offset)

    
def phonetic(sentences=items, offset=False):
    return _prim(".phn", sentences, offset)


def demo():
    from nltk_lite.corpora import timit

    print "sentence 5"
    print "----------"
    itemid = timit.items[5]
    spkrid, sentid = itemid.split(':')
    print "  item id:    ", itemid
    print "  speaker id: ", spkrid
    print "  sentence id:", sentid
    print
    record = timit.spkrinfo[spkrid]
    print "  speaker information:"
    print "    TIMIT speaker id: ", record[0]
    print "    speaker sex:      ", record[1]
    print "    dialect region:   ", record[2]
    print "    data type:        ", record[3]
    print "    recording date:   ", record[4]
    print "    date of birth:    ", record[5]
    print "    speaker height:   ", record[6]
    print "    speaker race:     ", record[7]
    print "    speaker education:", record[8]
    print "    comments:         ", record[9]
    print

    print "  words of the sentence:"
    print "   ", timit.raw(sentences=[itemid]).next()
    print

    print "  words of the sentence with offsets (first 3):"
    print "   ", timit.raw(sentences=[itemid], offset=True).next()[:3]
    print
    
    print "  phonemes of the sentence (first 10):"
    print "   ", timit.phonetic(sentences=[itemid]).next()[:10]
    print
    
    print "  phonemes of the sentence with offsets (first 3):"
    print "   ", timit.phonetic(sentences=[itemid], offset=True).next()[:3]
    print
    
    print "  looking up dictionary for words of the sentence..."
    words = timit.raw(sentences=[itemid]).next()
    for word in words:
        print "    %-5s:" % word, timit.dictionary[word]
    print

if __name__ == '__main__':
    demo()
