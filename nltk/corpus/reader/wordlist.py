# Natural Language Toolkit: Word List Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from util import *
from api import *
from nltk.internals import deprecated

class WordListCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def words(self, files=None):
        return concat([[w for w in open(filename).read().split('\n') if w]
                       for filename in self.abspaths(files)])

    def raw(self, files=None):
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

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
            
