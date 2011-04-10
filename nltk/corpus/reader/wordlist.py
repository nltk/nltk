# Natural Language Toolkit: Word List Corpus Reader
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.tokenize import line_tokenize

from util import *
from api import *

class WordListCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def words(self, fileids=None):
        return line_tokenize(self.raw(fileids))

    def raw(self, fileids=None):
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])


class SwadeshCorpusReader(WordListCorpusReader):
    def entries(self, fileids=None):
        """
        @return: a tuple of words for the specified fileids.
        """
        if not fileids:
            fileids = self.fileids()

        wordlists = [self.words(f) for f in fileids]
        return zip(*wordlists)
