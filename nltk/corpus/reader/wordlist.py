# Natural Language Toolkit: Word List Corpus Reader
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.internals import deprecated
from nltk.tokenize import line_tokenize

class WordListCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def words(self, files=None):
        return line_tokenize(self.raw(files))

    def raw(self, files=None):
        return concat([codecs.open(path, 'rb', enc).read()
                       for (path,enc) in self.abspaths(files, True)])

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
            
