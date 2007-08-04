# Natural Language Toolkit: Indian Language POS-Tagged Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Indian Language POS-Tagged Corpus
Collected by A Kumaran, Microsoft Research, India
Distributed with permission

Contents:
- Bangla: IIT Kharagpur
- Hindi: Microsoft Research India
- Marathi: IIT Bombay
- Telugu: IIIT Hyderabad
"""       

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk import tokenize
from nltk.tag import string2tags, string2words
import os

class IndianCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
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

    def words(self, items=None):
        return concat([IndianCorpusView(filename, False, False)
                       for filename in self._item_filenames(items)])

    def tagged_words(self, items=None):
        return concat([IndianCorpusView(filename, True, False)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        return concat([IndianCorpusView(filename, False, True)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        return concat([IndianCorpusView(filename, True, True)
                       for filename in self._item_filenames(items)])

    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]

    #{ Deprecated since 0.8
    from nltk.utilities import deprecated
    @deprecated("Use .raw() or .words() or .tagged_words() instead.")
    def read(items, format='tagged'):
        if format == 'raw': return self.raw(items)
        if format == 'tokenized': return self.words(items)
        if format == 'tagged': return self.tagged_words(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .words() instead.")
    def tokenized(items):
        return self.words(items)
    @deprecated("Use .tagged_words() instead.")
    def tagged(items):
        return self.tagged_words(items)
    #}
    
class IndianCorpusView(StreamBackedCorpusView):
    def __init__(self, corpus_file, tagged, group_by_sent):
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        StreamBackedCorpusView.__init__(self, corpus_file)

    def read_block(self, stream):
        line = stream.readline()
        if line.startswith('<'): return []
        sent = string2tags(line, sep='_')
        if not self._tagged: sent = [w for (w,t) in sent]
        if self._group_by_sent:
            return [sent]
        else:
            return sent

