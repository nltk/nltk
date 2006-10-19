#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox Data demonstration
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
corresponds to 
12.3.1   Accessing Toolbox Data
in http://nltk.sourceforge.net/lite/doc/en/data.html
"""

from nltk_lite.corpora import toolbox
from nltk_lite.etree import ElementTree
import sys

lexicon = toolbox.parse_corpus('rotokas.dic', key='lx')

sum_size = num_entries = 0
for entry in lexicon.findall('record'):
    num_entries += 1
    sum_size += len(entry)
print sum_size/num_entries

forth_entry = lexicon.findall('record')[3]
tree = ElementTree.ElementTree(forth_entry)
tree.write(sys.stdout)
