# Natural Language Toolkit: CONLL Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read conll-style chunk files.
"""       

from util import *
from api import *
from nltk import chunk, tree
import os

class ConllChunkCorpusReader(CorpusReader):
    def __init__(self, root, items, extension, chunk_types):
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension
        self.chunk_types = tuple(chunk_types)

    # Add method for list of tuples
    # add method for list of list of tuples

    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def words(self, items=None):
        return concat([ConllChunkCorpusView(filename, False, False, False)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        return concat([ConllChunkCorpusView(filename, False, True, False)
                       for filename in self._item_filenames(items)])

    def tagged_words(self, items=None):
        return concat([ConllChunkCorpusView(filename, True, False, False)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        return concat([ConllChunkCorpusView(filename, True, True, False)
                       for filename in self._item_filenames(items)])

    def chunked_words(self, items=None, chunk_types=None):
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, True, False, True,
                                            chunk_types)
                       for filename in self._item_filenames(items)])

    def chunked_sents(self, items=None, chunk_types=None):
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, True, True, True,
                                            chunk_types)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
class ConllChunkCorpusView(StreamBackedCorpusView):
    """
    """
    def __init__(self, corpus_file, tagged, group_by_sent, chunked, 
                 chunk_types=None):
        self._tagged = tagged
        self._chunked = chunked
        self._group_by_sent = group_by_sent
        self._chunk_types = chunk_types
        StreamBackedCorpusView.__init__(self, corpus_file)

    _DOCSTART = '-DOCSTART- -DOCSTART- O\n'
    def read_block(self, stream):
        # Read the next sentence.
        sent = read_blankline_block(stream)[0].strip()

        # Strip off the docstart marker, if present.
        if sent.startswith(self._DOCSTART):
            sent = sent[len(self._DOCSTART):].lstrip()
        
        # If format is chunked, use the conllstr2tree function to parse it.
        if self._chunked:
            # Use conllstr2tree to parse the tree.
            sent = chunk.conllstr2tree(sent, self._chunk_types)
            # Strip off POS tags, if requested:
            if not self._tagged:
                for i, child in enumerate(sent):
                    if isinstance(child, tree.Tree):
                        for j, child2 in enumerate(child):
                            child[j] = child2[0]
                    else:
                        sent[i] = child[0]

        # Otherwise, split the string into lines and select out either the
        # word&tag (tagged) or just the word (raw) from each line.
        else:
            lines = [line.split() for line in sent.split('\n')]
            if self._tagged:
                sent = [(word, tag) for (word, tag, chunk_typ) in lines]
            else:
                sent = [word for (word, tag, chunk_typ) in lines]

        # Return the result.
        if self._group_by_sent:
            return [sent]
        else:
            return list(sent)

