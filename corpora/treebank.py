# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from util import *
from nltk import tokenize, chunk, tree
from nltk.tag import tag2tuple
import os

"""
Penn Treebank corpus sample: tagged, NP-chunked, and parsed data from
Wall Street Journal for 3700 sentences.

This is a ~10% fragment of the Wall Street Journal section of the Penn
Treebank, (C) LDC 1995.  It is distributed with the Natural Language Toolkit
under the terms of the Creative Commons Attribution-NonCommercial-ShareAlike License
[http://creativecommons.org/licenses/by-nc-sa/2.5/].

Raw:

    Pierre Vinken, 61 years old, will join the board as a nonexecutive
    director Nov. 29.

Tagged:

    Pierre/NNP Vinken/NNP ,/, 61/CD years/NNS old/JJ ,/, will/MD join/VB 
    the/DT board/NN as/IN a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ./.

NP-Chunked:

    [ Pierre/NNP Vinken/NNP ]
    ,/, 
    [ 61/CD years/NNS ]
    old/JJ ,/, will/MD join/VB 
    [ the/DT board/NN ]
    as/IN 
    [ a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ]
    ./.

Parsed:

    ( (S 
      (NP-SBJ 
        (NP (NNP Pierre) (NNP Vinken) )
        (, ,) 
        (ADJP 
          (NP (CD 61) (NNS years) )
          (JJ old) )
        (, ,) )
      (VP (MD will) 
        (VP (VB join) 
          (NP (DT the) (NN board) )
          (PP-CLR (IN as) 
            (NP (DT a) (JJ nonexecutive) (NN director) ))
          (NP-TMP (NNP Nov.) (CD 29) )))
      (. .) ))
"""

def parsed(files = 'parsed', basedir = None):
    """
    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    if not basedir: basedir = get_basedir()

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        s = open(path).read()
        for t in tokenize.sexpr(s):
            try:
                yield tree.bracket_parse(t)
            except IndexError:
                # in case it's the real treebank format, 
                # strip first and last brackets before parsing
                yield tree.bracket_parse(t[1:-1]) 

def chunked(files = 'chunked', basedir = None):
    """
    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    if not basedir: basedir = get_basedir()

    for file in files:
        path = os.path.join(basedir, "treebank", file)
        s = open(path).read()
        for t in tokenize.blankline(s):
            yield chunk.tagstr2tree(t)

def tagged(files = 'chunked', basedir = None):
    """
    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{list(tuple)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    if not basedir: basedir = get_basedir()

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        f = open(path).read()
        for sent in tokenize.blankline(f):
            l = []
            for t in tokenize.whitespace(sent):
                if (t != '[' and t != ']'):
                    l.append(tag2tuple(t))
            yield l

def raw(files = 'raw', basedir = None):
    """
    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{list(string)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    if not basedir: basedir = get_basedir()

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        f = open(path).read()
        for sent in tokenize.blankline(f):
            l = []
            for t in tokenize.whitespace(sent):
                l.append(t)
            yield l


def demo():
    from nltk.corpora import treebank
    from itertools import islice

    print "Parsed:"
    for tree in islice(treebank.parsed(), 3):
        print tree.pp()
    print

    print "Chunked:"
    for tree in islice(treebank.chunked(), 3):
        print tree.pp()
    print

    print "Tagged:"
    for sent in islice(treebank.tagged(), 3):
        print sent
    print

    print "Raw:"
    for sent in islice(treebank.raw(), 3):
        print sent
    print

if __name__ == '__main__':
    demo()


