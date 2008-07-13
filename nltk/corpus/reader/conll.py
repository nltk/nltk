# Natural Language Toolkit: CONLL Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read CoNLL-style chunk files.
"""       

from util import *
from api import *
from nltk import chunk, tree
import os, codecs
from nltk.internals import deprecated

class ConllChunkCorpusReader(CorpusReader):
    """
    A CoNLL-style chunk corpus reader.
    """ 

    def __init__(self, root, files, chunk_types, encoding=None):
        CorpusReader.__init__(self, root, files, encoding)
        self.chunk_types = tuple(chunk_types)

    # Add method for list of tuples
    # add method for list of list of tuples

    def raw(self, files=None):
        return concat([codecs.open(path, 'rb', enc).read()
                       for (path,enc) in self.abspaths(files, True)])

    def words(self, files=None):
        return concat([ConllChunkCorpusView(filename, enc,
                                            False, False, False, False)
                       for (filename, enc) in self.abspaths(files, True)])

    def sents(self, files=None):
        return concat([ConllChunkCorpusView(filename, enc,
                                            False, True, False, False)
                       for (filename, enc) in self.abspaths(files, True)])

    def tagged_words(self, files=None):
        return concat([ConllChunkCorpusView(filename, enc,
                                            True, False, False, False)
                       for (filename, enc) in self.abspaths(files, True)])

    def tagged_sents(self, files=None):
        return concat([ConllChunkCorpusView(filename, enc,
                                            True, True, False, False)
                       for (filename, enc) in self.abspaths(files, True)])

    def chunked_words(self, files=None, chunk_types=None):
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, enc,
                                            True, False, True, False,
                                            chunk_types)
                       for (filename, enc) in self.abspaths(files, True)])

    def chunked_sents(self, files=None, chunk_types=None):
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, enc,
                                            True, True, True, False,
                                            chunk_types)
                       for (filename, enc) in self.abspaths(files, True)])

    def iob_words(self, files=None, chunk_types=None):
        """
        @return: a list of word/tag/IOB tuples 
        @rtype: C{list} of C{tuple}
        @param files: the list of files that make up this corpus 
        @type files: C{None} or C{str} or C{list}
        @param chunk_types: list of chunks to recognize when returning
                            tokens
        @type chunk_types: C{list} of C{str}
        """
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, enc,
                                            True, False, False, True,
                                            chunk_types)
                       for (filename, enc) in self.abspaths(files, True)])

    def iob_sents(self, files=None, chunk_types=None):
        """
        @return: a list of lists of word/tag/IOB tuples 
        @rtype: C{list} of C{list}
        @param files: the list of files that make up this corpus 
        @type files: C{None} or C{str} or C{list}
        @param chunk_types: list of chunks to recognize when returning
                            tokens
        @type chunk_types: C{list} of C{str}
        """
        if chunk_types is None: chunk_types = self.chunk_types
        return concat([ConllChunkCorpusView(filename, enc,
                                            True, True, True, True,
                                            chunk_types)
                       for (filename, enc) in self.abspaths(files, True)])

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
    A view of the CoNLL-style chunk corpus.  Subclasses 
    C{StreamBackedCorpusView}.
    """

    def __init__(self, corpus_file, encoding, tagged, group_by_sent,
                 chunked, iob, chunk_types=None):
        """
        Create a new CoNLL-style chunk corpus view.

        @param corpus_file: a corpus filename
        @type corpus_file: C{str}
        @param encoding: the unicode encoding that should be used to read the
                         file's contents
        @type encoding: C{str}
        @param tagged: flag indicating whether to return POS tags with tokens 
        @type tagged: C{bool}
        @param group_by_sent: flag indicating whether to return a list of
                              sentences, rather than a list of words
        @type group_by_sent: C{bool}
        @param chunked: flag indicating whether to return a list of chunks, 
                        rather than a list of sentences or words 
        @type chunked: C{bool}
        @param iob: flag indicating whether to return IOB tags with tokens
        @type iob: C{bool}
        @param chunk_types: list of chunks to recognize when returning
                            tokens
        @type chunk_types: C{list} of C{str}
        """
        self._tagged = tagged
        self._chunked = chunked
        self._group_by_sent = group_by_sent
        self._iob = iob
        self._chunk_types = chunk_types
        StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)

    _DOCSTART = '-DOCSTART- -DOCSTART- O\n'
    def read_block(self, stream):
        # Read the next sentence.
        sent = read_blankline_block(stream)[0].strip()

        # Strip off the docstart marker, if present.
        if sent.startswith(self._DOCSTART):
            sent = sent[len(self._DOCSTART):].lstrip()
        
        # If format is chunked and IOB tags are wanted, split the string into
        # lines and selected out the word&tag&iob tag else use the 
        # conllstr2tree function to parse it.
        if self._chunked:
            if self._iob:
                lines = [line.split() for line in sent.split('\n')]
                sent = [(word, tag, chunk_typ)
                        for (word, tag, chunk_typ) in lines]
            else:
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
        # word&tag&iob tag (IOB), word&tag (tagged) or just the word (raw) 
        # from each line.
        else:
            lines = [line.split() for line in sent.split('\n')]
            if self._iob:
                sent = [(word, tag, chunk_typ)
                        for (word, tag, chunk_typ) in lines]
            elif self._tagged:
                sent = [(word, tag) for (word, tag, chunk_typ) in lines]
            else:
                sent = [word for (word, tag, chunk_typ) in lines]

        # Return the result.
        if self._group_by_sent:
            return [sent]
        else:
            return list(sent)

