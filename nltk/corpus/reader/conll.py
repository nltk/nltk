# Natural Language Toolkit: CONLL Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
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
from nltk.internals import deprecated

class ConllChunkCorpusReader(CorpusReader):
    def __init__(self, root, files, chunk_types):
        CorpusReader.__init__(self, root, files)
        self.chunk_types = tuple(chunk_types)

    # Add method for list of tuples
    # add method for list of list of tuples

    def raw(self, files=None):
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

    def words(self, files=None):
        return concat([ConllChunkCorpusView(filename, False, False, False)
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        return concat([ConllChunkCorpusView(filename, False, True, False)
                       for filename in self.abspaths(files)])

    def tagged_words(self, files=None):
        return concat([ConllChunkCorpusView(filename, True, False, False)
                       for filename in self.abspaths(files)])

    def tagged_sents(self, files=None):
        return concat([ConllChunkCorpusView(filename, True, True, False)
                       for filename in self.abspaths(files)])

    def chunked_words(self, files=None, chunk_types=None):
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, True, False, True,
                                            chunk_types)
                       for filename in self.abspaths(files)])

    def chunked_sents(self, files=None, chunk_types=None):
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, True, True, True,
                                            chunk_types)
                       for filename in self.abspaths(files)])

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .words() or .tagged_words() or "
                ".chunked_sents() instead.")
    def read(self, items, format='chunked', chunk_types=None):
        if format == 'chunked': return self.chunked_sents(items, chunk_types)
        if format == 'raw': return self.raw(items)
        if format == 'tokenized': return self.words(items)
        if format == 'tagged': return self.tagged_words(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .chunked_sents() instead.")
    def chunked(self, items, chunk_types=None):
        return self.chunked_sents(items, chunk_types)
    @deprecated("Use .words() instead.")
    def tokenized(self, items):
        return self.words(items)
    @deprecated("Use .tagged_words() instead.")
    def tagged(self, items):
        return self.tagged_words(items)
    #}
    
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

