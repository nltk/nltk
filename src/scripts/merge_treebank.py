#!/usr/bin/env python
#
# Natural Language Toolkit: Treebank parse/tagged file merger
#
# Copyright (C) 2003 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

import os, os.path, sys
from nltk.corpus import treebank, set_basedir

def main(basedir=None):
    if basedir: set_basedir(basedir)

    # Find the root directory.
    rootdir = treebank.rootdir()
    if not os.path.isdir(rootdir):
        print 'Treebank corpus not found in %s; not merging.' % rootdir
        sys.exit(1)

    # Make sure the merged directory doesn't already exist.
    merged_dir = os.path.join(rootdir, 'merged')
    if os.path.exists(merged_dir):
        print 'Merged directory %s already exists.' % merged_dir
        print 'You must delete it if you want to re-generate merged files.'
        sys.exit(1)
        
    # Get the list of merged entries.  Be sure to do this *before* we
    # create the new merged directory.
    merged_entries = treebank.entries('merged')

    # Create the merged directory
    try: os.mkdir(merged_dir)
    except OSError, e:
        print 'Merge failed:', e
        sys.exit(1)

    # Write each (virtual) merged file to the merged directory
    print treebank
    for entry in merged_entries:
        print 'Merging %s...' % entry
        file = open(os.path.join(rootdir, entry), 'w')
        file.write(treebank.read(entry))
        file.close()

    print '%s files merged.' % len(merged_entries)

if __name__ == '__main__':
    if (len(sys.argv) > 2):# or (sys.argv[1][:1] == '-'):
        print 'Usage: %s [BASEDIR]' % sys.argv[0]
        print 'Where BASEDIR is the base directory for NLTK corpora'
        sys.exit(1)
    if len(sys.argv) == 2: main(sys.argv[1])
    else: main()
                               
