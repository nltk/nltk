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

documents = dict([('wsj_%04d' % i, 'Wall Street Journal document %d' % i)
                   for i in range(1, 100)])

def read_document(name, format='combined'):
    if format == 'combined':
        filename = find_corpus_file('treebank/combined', name, '.mrg')
        return StreamBackedCorpusView(filename, parsed_treebank_tokenizer)
    elif format == 'parsed':
        filename = find_corpus_file('treebank/parsed', name, '.prd')
        return StreamBackedCorpusView(filename, parsed_treebank_tokenizer)
    elif format == 'chunked':
        filename = find_corpus_file('treebank/tagged', name, '.pos')
        return StreamBackedCorpusView(filename, chunked_treebank_tokenizer)
    elif format == 'tagged':
        filename = find_corpus_file('treebank/tagged', name, '.pos')
        return StreamBackedCorpusView(filename, tagged_treebank_tokenizer)
    elif format == 'raw':
        filename = find_corpus_file('treebank/raw', name)
        return StreamBackedCorpusView(filename, raw_treebank_tokenizer)
    else:
        raise ValueError('Expected one of the following formats:\n'
                         'combined parsed chunked tagged raw')
read = read_document

def treebank_bracket_parse(t):
    try:
        return tree.bracket_parse(t)
    except IndexError:
        # in case it's the real treebank format, 
        # strip first and last brackets before parsing
        return tree.bracket_parse(t.strip()[1:-1]) 

def parsed_treebank_tokenizer(stream):
    return [treebank_bracket_parse(t) for t in 
            tokenize_sexpr(stream)]

def chunked_treebank_tokenizer(stream):
    return [chunk.tagstr2tree(t) for t in
            tokenize.blankline(stream.read())]

def tagged_treebank_tokenizer(stream):
    return [[tag2tuple(t) for t in tokenize.whitespace(sent)
             if t != '[' and t != ']']
            for sent in tokenize.blankline(stream.read())]

def raw_treebank_tokenizer(stream):
    return [list(tokenize.whitespace(sent))
            for sent in tokenize.blankline(stream.read())
            if sent.strip() != '.START']

def demo():
    from nltk.corpora import treebank
    from itertools import islice
    add_corpus_path('../../corpora')

    print "Parsed:"
    for tree in read('wsj_0003', format='parsed')[:3]:
        print tree
    print

    print "Chunked:"
    for tree in read('wsj_0003', format='chunked')[:3]:
        print tree
    print

    print "Tagged:"
    for sent in read('wsj_0003', format='tagged')[:3]:
        print sent
    print

    print "Raw:"
    for sent in read('wsj_0003', format='raw')[:3]:
        print sent
    print

if __name__ == '__main__':
    demo()


