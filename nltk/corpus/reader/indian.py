# Natural Language Toolkit: Indian Language POS-Tagged Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
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
import os
from nltk.internals import deprecated
import nltk.tag.util # for str2tuple

class IndianCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def words(self, files=None):
        return concat([IndianCorpusView(filename, False, False)
                       for filename in self.abspaths(files)])

    def tagged_words(self, files=None):
        return concat([IndianCorpusView(filename, True, False)
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        return concat([IndianCorpusView(filename, False, True)
                       for filename in self.abspaths(files)])

    def tagged_sents(self, files=None):
        return concat([IndianCorpusView(filename, True, True)
                       for filename in self.abspaths(files)])

    def raw(self, files=None):
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .words() or .tagged_words() instead.")
    def read(self, items, format='tagged'):
        if format == 'raw': return self.raw(items)
        if format == 'tokenized': return self.words(items)
        if format == 'tagged': return self.tagged_words(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .words() instead.")
    def tokenized(self, items):
        return self.words(items)
    @deprecated("Use .tagged_words() instead.")
    def tagged(self, items):
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
        sent = [nltk.tag.util.str2tuple(word, sep='_')
                for word in line.split()]
        if not self._tagged: sent = [w for (w,t) in sent]
        if self._group_by_sent:
            return [sent]
        else:
            return sent

