# Natural Language Toolkit: Names Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Names Corpus, Version 1.3 (1994-03-29)
Copyright (C) 1991 Mark Kantrowitz
Additions by Bill Ross

This corpus contains 5001 female names and 2943 male names, sorted
alphabetically, one per line.
(Used in NLTK with permission.  See the README file for details.)
"""       

from nltk_lite.corpora import get_basedir
import os

items = ['female', 'male']

item_name = {
    'female':     'Female names',
    'male':       'Male names'
    }

def raw(files = ['female', 'male']):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "names", file+".txt")
        for word in open(path).readlines():
            yield word.strip()

def demo():
    from nltk_lite.corpora import names
    from random import shuffle
    from pprint import pprint

    print "20 female names"
    female = list(names.raw('female'))
    shuffle(female)
    pprint(female[:20])

    print "20 male names"
    male = list(names.raw('male'))
    shuffle(male)
    pprint(male[:20])

if __name__ == '__main__':
    demo()

