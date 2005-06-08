# Natural Language Toolkit: Corpus access
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from tokenizer import whitespaceTokenize
from tagger import tag2tuple
import os.path
_basedir = "corpora"

def brown(files = list('abcdefghjklmnpr'), basedir = _basedir):

    """
    Read tokens from the Brown Corpus.

    Brown Corpus: A Standard Corpus of Present-Day Edited American
    English, for use with Digital Computers, by W. N. Francis and
    H. Kucera (1964), Department of Linguistics, Brown University,
    Providence, Rhode Island, USA.  Revised 1971, Revised and
    Amplified 1979.  Distributed with NLTK with the permission of the
    copyright holder.  Source: http://www.hit.uib.no/icame/brown/bcm.html

    The Brown Corpus is divided into the following files:

    a. press: reportage
    b. press: editorial
    c. press: reviews
    d. religion
    e. skill and hobbies
    f. popular lore
    g. belles-lettres
    h. miscellaneous: government & house organs
    j. learned
    k: fiction: general
    l: fiction: mystery
    m: fiction: science
    n: fiction: adventure
    p. fiction: romance
    r. humor
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(basedir, "brown_"+file)
        f = open(path).read()
        for sent in blanklineTokenize(f):
            l = []
            for t in whitespaceTokenize(sent):
                l.append(tag2tuple(t))
            yield l

from tokenizer import blanklineTokenize
import tree

def treebank_parsed(files = 'treebank_parsed', basedir = _basedir):

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
    @param basedir: Base directory of the files
    @type basedir: L{string}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        s = open("corpora/"+file).read()
        for t in blanklineTokenize(s):
            print t
            yield tree.parse(t)


def treebank_chunked(files = 'treebank_chunked', basedir = _basedir):

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
    @param basedir: Base directory of the files
    @type basedir: L{string}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(basedir, file)
        s = open(path).read()
        for t in blanklineTokenize(s):
            yield tree.chunk(t)


def treebank_tagged(files = 'treebank_chunked', basedir = _basedir):

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
    @param basedir: Base directory of the files
    @type basedir: L{string}
    @rtype: iterator over L{list(tuple)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(basedir, file)
        f = open(path).read()
        for sent in blanklineTokenize(f):
            l = []
            for t in whitespaceTokenize(sent):
                if (t != '[' and t != ']'):
                    l.append(tag2tuple(t))
            yield l

def treebank_raw(files = 'treebank_raw', basedir = _basedir):

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
    @param basedir: Base directory of the files
    @type basedir: L{string}
    @rtype: iterator over L{list(string)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(basedir, file)
        f = open(path).read()
        for sent in blanklineTokenize(f):
            l = []
            for t in whitespaceTokenize(sent):
                l.append(t)
            yield l


def demo():
    """
    Demonstrate corpus access for each of the defined corpora.
    """

    i=0
    for sent in brown(files='a'):
        print sent
        i+=1
        if i>5: break

    i=0
    for tree in treebank_parsed():
        print tree.pp()
        i+=1
        if i>3: break

    i=0
    for tree in treebank_chunked():
        print tree.pp()
        i+=1
        if i>3: break
    
    i=0
    for sent in treebank_tagged():
        print sent
        i+=1
        if i>3: break
    
    i=0
    for sent in treebank_raw():
        print sent
        i+=1
        if i>3: break
    
if __name__ == '__main__':
    demo()


