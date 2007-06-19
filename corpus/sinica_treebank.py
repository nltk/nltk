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

IDENTIFIER = re.compile(r'^#\S+\s')
APPENDIX = re.compile(r'(?<=\))#.*$')
TAGWORD = re.compile(r':([^:()|]+):([^:()|]+)')

def read_document(name='parsed', format=None):
    """
    @param name: 'parsed' or 'tagged' or 'raw'; or a filename.
    @param format: the format in which the results should be returned:
        one of 'parsed', 'tagged', or 'raw'.  If C{name} is a valid
        format (i.e., not a filename), then it will be used as the format.
    """
    if name in ('parsed', 'tagged', 'raw'):
        format = name
        if name == 'tagged': name = 'parsed'
    if format == 'parsed':
        filename = find_corpus_file('sinica_treebank', name)
        return StreamBackedCorpusView(filename, parsed_sinica_tb_tokenizer)
    elif format == 'tagged':
        filename = find_corpus_file('sinica_treebank', name)
        return StreamBackedCorpusView(filename, tagged_sinica_tb_tokenizer)
    elif format == 'raw':
        filename = find_corpus_file('sinica_treebank', name)
        return StreamBackedCorpusView(filename, raw_sinica_tb_tokenizer)
    else:
        raise ValueError('Expected one of the following formats:\n'
                         'combined parsed chunked tagged raw')
read = read_document

def raw_sinica_tb_tokenizer(stream):
    return [stream.readline().split()[1:]]

def tagged_sinica_tb_tokenizer(stream):
    sent = stream.readline()
    sent = re.sub(IDENTIFIER, '', sent)
    tagged_tokens = re.findall(TAGWORD, sent)
    return [[(token, tag) for (tag, token) in tagged_tokens]]

def parsed_sinica_tb_tokenizer(stream):
    sent = stream.readline()
    sent = re.sub(IDENTIFIER, '', sent)
    sent = re.sub(APPENDIX, '', sent)
    return [tree.sinica_parse(sent)]

def demo():
    from nltk.corpus import sinica_treebank
    from nltk.draw.tree import draw_trees
    
    print "Raw:"
    for sent in sinica_treebank.read('raw')[:10]:
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

    draw_trees(*trees)

if __name__ == '__main__':
    demo()


