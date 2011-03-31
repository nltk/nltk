#!/usr/bin/env python
#
# Natural Language Toolkit: Example generation script
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Extract the code samples from a file in restructured text format
"""

import sys

from epydoc.markup.doctest import DoctestColorizer
PROMPT_RE = DoctestColorizer.PROMPT_RE        

for filename in sys.argv[1:]:
    in_code = False
    for line in open(filename).readlines():
        if PROMPT_RE.match(line):
            in_code = True
            print(PROMPT_RE.sub('', line), end=' ')

        elif in_code:
            in_code = False
            print()
