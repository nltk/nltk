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
    def __init__(self, delimiter=' '):
        """
        @param root: The root directory for this corpus.
        @param files: A list or regexp specifying the files in this corpus.
        @param delimiter: Field delimiter
        """
        CorpusReader.__init__(self, root, files)
        self._delimiter = delimiter

    def tuples(self, files):
        return concat([StreamBackedCorpusView(filename, self._read_tuple_block)
                       for filename in self.abspaths(files)])

    def raw(self, files):
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

    def _read_tuple_block(self, stream):
        line = stream.readline().strip()
        if line:
            return [tuple(line.split(self._delimiter, 1))]
        else:
            return []
