# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
from nltk_lite.tag import tag2tuple
from nltk_lite.parse import tree
import os

def parsed(files = 'parsed'):

    """
    Read trees from the Penn Treebank corpus sample.

    This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
    available under fair use for the purposes of illustrating NLTK
    tools for tokenizing, tagging, chunking and parsing.  This data is
    for non-commercial use only.

    Contents: parsed data from Wall Street Journal for 1650 sentences, e.g.:

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

    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        s = open(path).read()
        for t in tokenize.blankline(s):
            yield tree.bracket_parse(t)


def chunked(files = 'chunked'):

    """
    Read chunks from the Penn Treebank corpus sample.

    This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
    available under fair use for the purposes of illustrating NLTK
    tools for tokenizing, tagging, chunking and parsing.  This data is
    for non-commercial use only.

    Contents: chunked data from Wall Street Journal for 1650 sentences, e.g.:

    [ Pierre/NNP Vinken/NNP ]
    ,/, 
    [ 61/CD years/NNS ]
    old/JJ ,/, will/MD join/VB 
    [ the/DT board/NN ]
    as/IN 
    [ a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ]
    ./.

    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        s = open(path).read()
        for t in tokenize.blankline(s):
            yield tree.chunk(t)


def tagged(files = 'chunked'):

    """
    Read tagged sentences from the Penn Treebank corpus sample.

    This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
    available under fair use for the purposes of illustrating NLTK
    tools for tokenizing, tagging, chunking and parsing.  This data is
    for non-commercial use only.

    Contents: tagged data from Wall Street Journal for 1650 sentences, e.g.:

    Pierre/NNP Vinken/NNP ,/, 61/CD years/NNS old/JJ ,/, will/MD join/VB 
    the/DT board/NN as/IN a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ./.

    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{list(tuple)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        f = open(path).read()
        for sent in tokenize.blankline(f):
            l = []
            for t in tokenize.whitespace(sent):
                if (t != '[' and t != ']'):
                    l.append(tag2tuple(t))
            yield l

def raw(files = 'raw'):
    """
    Read sentences from the Penn Treebank corpus sample.

    This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
    available under fair use for the purposes of illustrating NLTK
    tools for tokenizing, tagging, chunking and parsing.  This data is
    for non-commercial use only.

    Contents: tagged data from Wall Street Journal for 1650 sentences, e.g.:

    Pierre Vinken , 61 years old , will join the board as a nonexecutive
    director Nov. 29 .

    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{list(string)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        f = open(path).read()
        for sent in tokenize.blankline(f):
            l = []
            for t in tokenize.whitespace(sent):
                l.append(t)
            yield l


def demo():
    from nltk_lite.corpora import treebank
    from itertools import islice

    for tree in islice(treebank.parsed(), 3):
        print tree.pp()

    for tree in islice(treebank.chunked(), 3):
        print tree.pp()

    for sent in islice(treebank.tagged(), 3):
        print sent

    for sent in islice(treebank.raw(), 3):
        print sent

if __name__ == '__main__':
    demo()


