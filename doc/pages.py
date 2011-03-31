#!/usr/bin/env python
#
# Natural Language Toolkit: Page length extraction script
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""

This script extracts the pagecount from a latex log file.

"""

from sys import argv
from re import search

regexp = r'\[(\d+)\][^\[]*$'       # last [nn] in file
logfile = open(argv[1]).read()     # latex logfile
print((search(regexp, logfile).group(1)))
