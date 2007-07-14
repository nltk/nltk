# Natural Language Toolkit: Sinica Treebank Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from util import *
from nltk import tokenize, tree
from nltk.tag import tag2tuple
import os, re

"""
Sinica Treebank Corpus Sample

http://rocling.iis.sinica.edu.tw/CKIP/engversion/treebank.htm

10,000 parsed sentences, drawn from the Academia Sinica Balanced
Corpus of Modern Chinese.  Parse tree notation is based on
Information-based Case Grammar.  Tagset documentation is available
at http://www.sinica.edu.tw/SinicaCorpus/modern_e_wordtype.html

Language and Knowledge Processing Group, Institute of Information
Science, Academia Sinica

It is distributed with the Natural Language Toolkit under the terms of
the Creative Commons Attribution-NonCommercial-ShareAlike License
[http://creativecommons.org/licenses/by-nc-sa/2.5/].

References:

Feng-Yi Chen, Pi-Fang Tsai, Keh-Jiann Chen, and Chu-Ren Huang (1999)
The Construction of Sinica Treebank. Computational Linguistics and
Chinese Language Processing, 4, pp 87-104.

Huang Chu-Ren, Keh-Jiann Chen, Feng-Yi Chen, Keh-Jiann Chen, Zhao-Ming
Gao, and Kuang-Yu Chen. 2000. Sinica Treebank: Design Criteria,
Annotation Guidelines, and On-line Interface. Proceedings of 2nd
Chinese Language Processing Workshop, Association for Computational
Linguistics.

Chen Keh-Jiann and Yu-Ming Hsieh (2004) Chinese Treebanks and Grammar
Extraction, Proceedings of IJCNLP-04, pp560-565.
"""

#: A list of all documents in this corpus.
items = ['parsed', 'tagged', 'tokenized', 'raw']

IDENTIFIER = re.compile(r'^#\S+\s')
APPENDIX = re.compile(r'(?<=\))#.*$')
TAGWORD = re.compile(r':([^:()|]+):([^:()|]+)')

def read_document(item='parsed', format=None):
    """
    @param item: 'parsed' or 'tagged' or 'tokenized'; or a filename.
    @param format: the format in which the results should be returned:
        one of 'parsed', 'tagged', or 'tokenized'.  If C{item} is a valid
        format (i.e., not a filename), then it will be used as the format.
    """
    if isinstance(item, list):
        return concat([read(doc, format) for doc in item])
    if item in ('parsed', 'tagged', 'tokenized', 'raw'):
        format = item
        if item == 'tokenized': item = 'raw'
        if item in ('tagged', 'raw'): item = 'parsed'
        
    filename = find_corpus_file('sinica_treebank', item)
    if format == 'raw':
        return open(filename).read()
    if format == 'parsed':
        return StreamBackedCorpusView(filename, read_parsed_sinica_block)
    elif format == 'tagged':
        return StreamBackedCorpusView(filename, read_tagged_sinica_block)
    elif format == 'tokenized':
        return StreamBackedCorpusView(filename, read_tokenized_sinica_block)
    else:
        raise ValueError('Expected one of the following formats:\n'
                         'combined parsed chunked tagged tokenized')
read = read_document

def read_tokenized_sinica_block(stream):
    return [stream.readline().split()[1:]]

def read_tagged_sinica_block(stream):
    sent = stream.readline()
    sent = re.sub(IDENTIFIER, '', sent)
    tagged_tokens = re.findall(TAGWORD, sent)
    return [[(token, tag) for (tag, token) in tagged_tokens]]

def read_parsed_sinica_block(stream):
    sent = stream.readline()
    sent = re.sub(IDENTIFIER, '', sent)
    sent = re.sub(APPENDIX, '', sent)
    return [tree.sinica_parse(sent)]

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def tagged(item='parsed'):
    """@return: the given document as a list of sentences, where each
    sentence is a list of tagged words.  Tagged words are encoded as
    tuples of (word, part-of-speech)."""
    return read_document(item, format='tagged')

def tokenized(item='raw'):
    """@return: the given document as a list of sentences, where each
    sentence is a list of words."""
    return read_document(item, format='tokenized')

def raw(item='parsed'):
    """@return: the given document as a single string."""
    return read_document(item, format='raw')

def parsed(item='parsed'):
    """@return: the given document as a list of parse trees."""
    return read_document(item, format='parsed')

######################################################################
#{ Demo
######################################################################

def demo(draw=True):
    from nltk.corpus import sinica_treebank
    from nltk.draw.tree import draw_trees
    
    print "Tokenized:"
    for sent in sinica_treebank.read('tokenized')[:10]:
        print sent
    print

    print "Tagged:"
    for sent in sinica_treebank.read('tagged')[:10]:
        print sent
    print

    print "Parsed:"
    trees = list(sinica_treebank.read('parsed')[:10])
    for tree in trees:
        print tree
    print

    if draw:
        draw_trees(*trees)

if __name__ == '__main__':
    demo()


