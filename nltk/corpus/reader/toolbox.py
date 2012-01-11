# Natural Language Toolkit: Toolbox Reader
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
#         Stuart Robinson <Stuart.Robinson@mpi.nl>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Module for reading, writing and manipulating
Toolbox databases and settings fileids.
"""

import os
import re
import codecs

from nltk.toolbox import ToolboxData

from util import *
from api import *

class ToolboxCorpusReader(CorpusReader):
    def xml(self, fileids, key=None):
        return concat([ToolboxData(path, enc).parse(key)
                       for (path, enc) in self.abspaths(fileids, True)])

    def fields(self, fileids, strip=True, unwrap=True, encoding=None,
               errors='strict', unicode_fields=None):
        return concat([list(ToolboxData(fileid,enc).fields(
                             strip, unwrap, encoding, errors, unicode_fields))
                       for (fileid, enc)
                       in self.abspaths(fileids, include_encoding=True)])

    # should probably be done lazily:
    def entries(self, fileids, **kwargs):
        if 'key' in kwargs:
            key = kwargs['key']
            del kwargs['key']
        else:
            key = 'lx'  # the default key in MDF
        entries = []
        for marker, contents in self.fields(fileids, **kwargs):
            if marker == key:
                entries.append((contents, []))
            else:
                try:
                    entries[-1][-1].append((marker, contents))
                except IndexError:
                    pass
        return entries

    def words(self, fileids, key='lx'):
        return [contents for marker, contents in self.fields(fileids) if marker == key]

    def raw(self, fileids):
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])


def demo():
    pass

if __name__ == '__main__':
    demo()
