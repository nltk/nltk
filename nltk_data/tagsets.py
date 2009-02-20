# Natural Language Toolkit (NLTK) Package for Tagset Tables
#
# Copyright (C) 2001-2009 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A package for building the Tagset Tables distributed with NLTK
"""

import re
import pickle

from tagset_data import *

RECORD_SEP = "   *"
FIELD_SEP = " - "

TAGSETS = {'upenn_tagset': upenn_tagset,
           'brown_tagset': brown_tagset,
           'claws5_tagset': claws5_tagset}

def load_tagset(s):
    tagset = {}
    entries = s.split(RECORD_SEP)
    for entry in entries:
        if FIELD_SEP in entry:
            entry = re.sub(r'(?m)\s+', ' ', entry)
            _, tag, defn, examples = entry.split(FIELD_SEP, 3)
            if tag not in tagset:
                tagset[tag] = (defn, examples)
            else:
                raise ValueError, "Duplicate tag: %s" % tag
    return tagset

def build_tagsets():
    for tagset in TAGSETS:
        print "Building", tagset 
        output = open(tagset + ".pickle", "w")
        tagset_dict = load_tagset(TAGSETS[tagset])
        pickle.dump(tagset_dict, output)
        output.close()
    
if __name__ == '__main__':
    build_tagsets()
