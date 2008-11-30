#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox Data demonstration
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
corresponds to 
12.3.1   Accessing Toolbox Data
in http://nltk.sourceforge.net/lite/doc/en/data.html
"""

from nltk.corpus import toolbox

lexicon = toolbox.xml('rotokas.dic')

sum_size = num_entries = 0
for entry in lexicon.findall('record'):
    num_entries += 1
    sum_size += len(entry)
print sum_size/num_entries


from nltk.etree.ElementTree import ElementTree
import sys
fourth_entry = lexicon.findall('record')[3]
tree = ElementTree(fourth_entry)
tree.write(sys.stdout)
