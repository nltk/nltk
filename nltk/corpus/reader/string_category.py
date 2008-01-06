# Natural Language Toolkit: String Category Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tuples from a corpus consisting of categorized strings.
For example, from the question classification corpus:

NUM:dist How far is it from Denver to Aspen ?
LOC:city What county is Modesto , California in ?
HUM:desc Who was Galileo ?
DESC:def What is an atom ?
NUM:date When did Hawaii become a state ?
"""       

# based on PPAttachmentCorpusReader

from util import *
from api import *
import os

class StringCategoryCorpusReader(CorpusReader):
    def __init__(self, root, documents, extension='', delimiter=' '):
        """
        @param root: The root directory for this corpus.
        @param documents: A list of documents in this corpus.
        @param extension: File extension for documents in this corpus.
        @param delimiter: Field delimiter
        """
        if isinstance(documents, basestring):
            documents = find_corpus_items(root, documents, extension)
        self._root = root
        self._documents = tuple(documents)
        self._extension = extension
        self._delimiter = delimiter

    def tuples(self, documents):
        return concat([StreamBackedCorpusView(filename, self._read_tuple_block)
                       for filename in self.filenames(documents)])

    def raw(self, documents):
        return concat([open(filename).read()
                       for filename in self.filenames(documents)])

    def _read_tuple_block(self, stream):
        line = stream.readline().strip()
        if line:
            return [tuple(line.split(self._delimiter, 1))]
        else:
            return []
