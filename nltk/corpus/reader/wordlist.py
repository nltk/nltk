# Natural Language Toolkit: Word List Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from util import *
from api import *
from nltk.utilities import deprecated

class WordListCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def __init__(self, root, documents, extension=''):
        """
        @param root: The root directory for this corpus.
        @param documents: A list of documents in this corpus.
        @param extension: File extension for documents in this corpus.
        """
        if isinstance(documents, basestring):
            documents = find_corpus_items(root, documents, extension)
        self._root = root
        self._documents = tuple(documents)
        self._extension = extension

    def words(self, documents=None):
        return concat([[w for w in open(filename).read().split('\n') if w]
                       for filename in self.filenames(documents)])

    def raw(self, documents=None):
        return concat([open(filename).read()
                       for filename in self.filenames(documents)])

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .words() instead.")
    def read(self, items=None, format='listed'):
        if format == 'raw': return self.raw(items)
        if format == 'listed': return self.words(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .words() instead.")
    def listed(self, items=None):
        return self.words(items)
    #}
            
