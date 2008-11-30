#!/usr/bin/env python
#
## Natural Language Toolkit: substitute a pattern with a replacement in every file
#
# Copyright (C) 2008 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id:$

# NB Should work on all platforms, http://www.python.org/doc/2.5.2/lib/os-file-dir.html

import os, stat, sys

def update(file, pattern, replacement, verbose=False):
    if verbose:
        print "Updating:", file

    # make sure we can write the file   
    old_perm = os.stat(file)[0]
    if not os.access(file, os.W_OK):
        os.chmod(file, old_perm | stat.S_IWRITE)

    # write the file
    s = open(file, 'rb').read()
    out = open(file, 'wb')
    out.write(s.replace(pattern, replacement))
    out.close()
   
    # restore permissions
    os.chmod(file, old_perm)

if len(sys.argv) != 3:
    exit("Usage: %s <pattern> <replacement>" % sys.argv[0])

pattern = sys.argv[1]
replacement = sys.argv[2]

for root, dirs, files in os.walk('.'):
    if '/.svn' not in root:
        for file in files:
            path = os.path.join(root, file)
            update(path, pattern, replacement)

