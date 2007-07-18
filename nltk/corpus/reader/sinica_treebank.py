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


class SinicaTreebankCorpusReader:
    """
    Reader for corpora that consist of treebank-style trees.  For
    reading the Treebank corpus itself, you may wish to use
    L{TreebankCorpusReader}, which combines this reader with readers
    for the other formats available in the treebank.
    """
    def __init__(self, root, items, extension=''):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension

    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def parsed_sents(self, items=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_parsed_block)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_tagged_block)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_sent_block)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
        
    def _read_sent_block(self, stream):
        sent = stream.readline()
        sent = re.sub(IDENTIFIER, '', sent)
        tagged_tokens = re.findall(TAGWORD, sent)
        return [[token for (tag, token) in tagged_tokens]]

    def _read_tagged_block(self, stream):
        sent = stream.readline()
        sent = re.sub(IDENTIFIER, '', sent)
        tagged_tokens = re.findall(TAGWORD, sent)
        return [[(token, tag) for (tag, token) in tagged_tokens]]
    
    def _read_parsed_block(self, stream):
        sent = stream.readline()
        sent = re.sub(IDENTIFIER, '', sent)
        sent = re.sub(APPENDIX, '', sent)
        return [tree.sinica_parse(sent)]

######################################################################
#{ Demo
######################################################################

def demo(draw=True):
    from nltk.corpus import sinica_treebank
    from nltk.draw.tree import draw_trees
    
    print "Tokenized:"
    for sent in sinica_treebank.sents()[:10]:
        print sent
    print

    print "Tagged:"
    for sent in sinica_treebank.tagged_sents()[:10]:
        print sent
    print

    print "Parsed:"
    trees = list(sinica_treebank.parsed_sents()[:10])
    for tree in trees:
        print tree
    print

    if draw:
        draw_trees(*trees)

if __name__ == '__main__':
    demo()


