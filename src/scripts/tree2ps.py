# Natural Language Toolkit: Tree->Postscript Converter
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Draw the treebank-style tree(s) in the given file(s), and output the
result as postscript file(s).  

Usage::
    tree2ps.py input.txt output.ps
"""

from nltk.tree import parse_treebank
from nltk.draw.tree import print_tree
import sys

def usage(progname):
    print """
Usage::
    %s input.txt output.ps
    """ % progname
    sys.exit()

def error(progname, msg):
    print "%s: %s" % (progname, msg)
    sys.exit()

def convert(infile, outfile, verbose):
    if verbose > 1: print "Reading %s..." % infile
    try:
        input = open(infile, 'r').read()
    except:
        error("Could not read input file %s." % infile)

    if verbose > 1: print "Processing %s..." % infile
    try:
        tree = parse_treebank(input)
    except:
        error("Error parsing the input file %s." % infile)

    if verbose > 1: print "Printing the tree to %s..." % outfile
    try:
        print_tree(tree, outfile)
    except:
        error("Error printing the tree to %s." % outfile)

    if verbose > 0:
        print 'Converted %s->%s' % (infile, outfile)

def process_args(argv):
    """
    @return: A dictionary of params.  Current params are:
        - infile
        - outfile
        - verbose
    """
    params = {'verbose': 0}
    for arg in argv:
        if arg[0] == '-':
            if arg == '-v':
                params['verbose'] += 1
            else:
                usage()
        elif not params.has_key('infile'): params['infile'] = arg
        elif not params.has_key('outfile'): params['outfile'] = arg
        else: usage()

    if not params.has_key('outfile'): usage()
    return params

    
if __name__ == '__main__':
    params = process_args(sys.argv)
    convert(params['infile'], params['outfile'], params['verbose'])
