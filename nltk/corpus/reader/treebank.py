# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Penn Treebank corpus sample: tagged, NP-chunked, and parsed data from
Wall Street Journal for 3700 sentences.

This is a ~10% fragment of the Wall Street Journal section of the Penn
Treebank, (C) LDC 1995.  It is distributed with the Natural Language
Toolkit under the terms of the Creative Commons
Attribution-NonCommercial-ShareAlike License
[http://creativecommons.org/licenses/by-nc-sa/2.5/].
"""
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader
from nltk.corpus.reader.chunked import ChunkedCorpusReader
from nltk.tree import Tree
from nltk import tokenize, chunk
import os.path

class TreebankCorpusReader(CorpusReader):
    """
    Corpus reader for the treebank.  Combines thee underlying formats:
    parsed, tagged+chunkied, and plaintext.  Each of these formats is
    stored in a different subdirectory (combined/, tagged/, and raw/,
    respectively).

    If your corpus doesn't have this format, but just contains files
    with treebank-style parses, you should use
    L{BracketParseCorpusReader} instead.
    """
    def __init__(self, root):
        self._root = root
        self._mrg_reader = BracketParseCorpusReader(
            os.path.join(root, 'combined'), '.*', '.mrg')
        self._pos_reader = ChunkedCorpusReader(
            os.path.join(root, 'tagged'), '.*', '.pos',
            sent_tokenizer=tagged_treebank_sent_tokenizer,
            para_block_reader=tagged_treebank_para_block_reader)

        # Make sure we have a consistent set of items:
        if set(self._mrg_reader.items) != set(self._pos_reader.items):
            raise ValueError('Items in "combined" and "tagged" '
                             'subdirectories do not match.')
        for item in self._mrg_reader.items:
            if not os.path.exists(os.path.join(root, 'raw', item)):
                raise ValueError('File %r missing from "raw" subdirectory'
                                 % item)
        self._items = self._mrg_reader.items

    root = property(lambda self: self._root, doc="""
        The directory where this corpus is stored..""")

    items = property(lambda self: self._items, doc="""
        A list of the documents in this corpus""")
    
    # Delegate to one of our two sub-readers:
    def words(self, items=None):
        return self._pos_reader.words(items)
    def sents(self, items=None):
        return self._pos_reader.sents(items)
    def paras(self, items=None):
        return self._pos_reader.paras(items)
    def tagged_words(self, items=None):
        return self._pos_reader.tagged_words(items)
    def tagged_sents(self, items=None):
        return self._pos_reader.tagged_sents(items)
    def tagged_paras(self, items=None):
        return self._pos_reader.tagged_paras(items)
    def chunked_words(self, items=None):
        return self._pos_reader.chunked_words(items)
    def chunked_sents(self, items=None):
        return self._pos_reader.chunked_sents(items)
    def chunked_paras(self, items=None):
        return self._pos_reader.chunked_paras(items)
    def parsed_sents(self, items=None):
        return self._mrg_reader.parsed_sents(items)

    # Read in the text file, and strip the .START prefix.
    def text(self, items=None):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        filenames = [os.path.join(self._root, 'raw', item) for item in items]
        return concat([re.sub(r'\A\s*\.START\s*', '', open(filename).read())
                       for filename in filenames])

def tagged_treebank_sent_tokenizer(para):
    return tokenize.regexp(para, r'(?<=/\.)\s', gaps=True)

def tagged_treebank_para_block_reader(stream):
    # Read the next paragraph.
    para = ''
    while True:
        line = stream.readline()
        # End of paragraph:
        if re.match('======+\s*$', line):
            if para.strip(): return [para]
        # End of file:
        elif line == '':
            if para.strip(): return [para]
            else: return []
        # Content line:
        else:
            para += line
            
######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import treebank

    print "Parsed:"
    for tree in treebank.parsed_sents('wsj_0003')[:3]:
        print tree
    print

    print "Chunked:"
    for tree in treebank.chunked_sents('wsj_0003')[:3]:
        print tree
    print

    print "Tagged:"
    for sent in treebank.tagged_sents('wsj_0003')[:3]:
        print sent
    print

    print "Words:"
    print ' '.join(treebank.words('wsj_0120')[:30])

    # Note that this spans across multiple documents:
    print 'Height of trees:'
    for tree in treebank.parsed_sents()[:25]:
        print tree.height(),

if __name__ == '__main__':
    demo()


