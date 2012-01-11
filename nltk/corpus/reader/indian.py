# Natural Language Toolkit: Indian Language POS-Tagged Corpus Reader
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
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

import codecs

from nltk.tag.util import str2tuple

from util import *
from api import *

class IndianCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def words(self, fileids=None):
        return concat([IndianCorpusView(fileid, enc,
                                        False, False)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def tagged_words(self, fileids=None, simplify_tags=False):
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([IndianCorpusView(fileid, enc,
                                        True, False, tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def sents(self, fileids=None):
        return concat([IndianCorpusView(fileid, enc,
                                        False, True)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def tagged_sents(self, fileids=None, simplify_tags=False):
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([IndianCorpusView(fileid, enc,
                                        True, True, tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def raw(self, fileids=None):
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])


class IndianCorpusView(StreamBackedCorpusView):
    def __init__(self, corpus_file, encoding, tagged,
                 group_by_sent, tag_mapping_function=None):
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._tag_mapping_function = tag_mapping_function
        StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)

    def read_block(self, stream):
        line = stream.readline()
        if line.startswith('<'):
            return []
        sent = [str2tuple(word, sep='_') for word in line.split()]
        if self._tag_mapping_function:
            sent = [(w, self._tag_mapping_function(t)) for (w,t) in sent]
        if not self._tagged: sent = [w for (w,t) in sent]
        if self._group_by_sent:
            return [sent]
        else:
            return sent


