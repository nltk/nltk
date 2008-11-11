#!/usr/bin/env python
#
## Natural Language Toolkit: update svn repository to new UUID
#
# Copyright (C) 2008 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
# $Id:$

# NB Should work on all platforms, http://www.python.org/doc/2.5.2/lib/os-file-dir.html

import os, stat

old_uuid = "eec68fb5-7d10-0410-9b68-e0257d698959" # NLTK at SourceForge
new_uuid = "566ae9b8-8506-11dd-a143-0dd59a09f4aa" # NLTK at GoogleCode

def update(file):
    print "Updating:", file

    # make sure we can write the file   
    old_perm = os.stat(file)[0]
    if not os.access(file, os.W_OK):
        os.chmod(file, old_perm | stat.S_IWRITE)

    # write the file
    s = open(file, 'rb').read()
    out = open(file, 'wb')
    out.write(s.replace(old_uuid, new_uuid))
    out.close()
   
    # restore permissions
    os.chmod(file, old_perm)

for root, dirs, files in os.walk('.'):
   if root.endswith('.svn'):
       update(os.path.join(root, 'entries'))

