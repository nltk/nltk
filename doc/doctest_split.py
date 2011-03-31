#!/usr/bin/env python
#
# Natural Language Toolkit: Split an RST file into sections for independent doctest checking
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import sys
import re

EXT = "doctest"              # output filename extension
SEC = r"\n(?=-+\n.+\n-+\n)"  # pattern to match section heading

# include this at the top of each output file
HDR = """
    >>> from __future__ import division
    >>> import nltk, re, pprint
"""

for filename in sys.argv[1:]:
    contents = open(filename).read()
    basename, suffix = filename.split('.')
    for count, section in enumerate(re.split(SEC, contents)):
        chunk_name = "%s-%d.%s" % (basename, count+1, EXT)
        chunk_file = open(chunk_name, "w")
        chunk_file.write(HDR + "\n")
        chunk_file.write(section)
        chunk_file.close()
