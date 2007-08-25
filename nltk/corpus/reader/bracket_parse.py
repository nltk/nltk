# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.tree import bracket_parse
import os.path

"""
Corpus reader for corpora that consist of parenthesis-delineated parse
trees.
"""

class BracketParseCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of parenthesis-delineated parse
    trees.
    """
    def __init__(self, root, items, extension='', comment_char=None):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        @param comment: The character which can appear at the start of a line to
          indicate that the rest of the line is a comment.
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension
        self._comment_char = comment_char

    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def parsed_sents(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_parsed_sent_block)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_tagged_sent_block)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_sent_block)
                       for filename in self._item_filenames(items)])

    def tagged_words(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_tagged_word_block)
                       for filename in self._item_filenames(items)])

    def words(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_word_block)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
        
# block readers

    def _read_word_block(self, stream):
        return sum(self._read_sent_block(stream), [])

    def _read_tagged_word_block(self, stream):
        return sum(self._read_tagged_sent_block(stream), [])

    def _read_sent_block(self, stream):
        return [self._word(t) for t in read_sexpr_block(stream, comment_char=self._comment_char)]
    
    def _read_tagged_sent_block(self, stream):
        return [self._tag(t) for t in read_sexpr_block(stream, comment_char=self._comment_char)]

    def _read_parsed_sent_block(self, stream):
        trees = [self._parse(t) for t in read_sexpr_block(stream, comment_char=self._comment_char)]
        return [tree for tree in trees if tree is not None]
    
# low-level string processing
    
    def _normalize(self, t):
        # If there's an empty set of brackets surrounding the actual
        # parse, then strip them off.
        if re.match(r'\s*\(\s*\(', t):
            t = t.strip()[1:-1]
        # Replace any punctuation leaves of the form (!), (,), with (! !), (, ,)
        t = re.sub(r"\((.)\)", r"(\1 \1)", t)
        return t

    def _parse(self, t):
        return bracket_parse(self._normalize(t))

    def _tag(self, t):
        return [(w,t) for (t,w) in re.findall(r'\((\S+?) (\S+?)\)', self._normalize(t))]

    def _word(self, t):
        return re.findall(r'\(\S+? (\S+?)\)', self._normalize(t))

