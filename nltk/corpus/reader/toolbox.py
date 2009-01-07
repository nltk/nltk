#!/usr/bin/env python

# Natural Language Toolkit: Toolbox Reader
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
#         Stuart Robinson <Stuart.Robinson@mpi.nl>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Module for reading, writing and manipulating 
Toolbox databases and settings files.
"""

import os, re, codecs
from nltk.toolbox import ToolboxData
from nltk.internals import deprecated
from nltk import data

from util import *
from api import *

class ToolboxCorpusReader(CorpusReader):
    def xml(self, files, key=None):
        return concat([ToolboxData(path, enc).parse(key)
                       for (path, enc) in self.abspaths(files, True)])

    def fields(self, files, strip=True, unwrap=True, encoding=None,
               errors='strict', unicode_fields=None):
        return concat([list(ToolboxData(filename,enc).fields(
                             strip, unwrap, encoding, errors, unicode_fields))
                       for (filename, enc)
                       in self.abspaths(files, include_encoding=True)])

    # should probably be done lazily:
    def entries(self, files, **kwargs):
        if 'key' in kwargs:
            key = kwargs['key']
            del kwargs['key']
        else:
            key = 'lx'  # the default key in MDF
        entries = []
        for marker, contents in self.fields(files, **kwargs):
            if marker == key:
                entries.append((contents, []))
            else:
                try:
                    entries[-1][-1].append((marker, contents))
                except IndexError:
                    pass
        return entries

    def words(self, files, key='lx'):
        return [contents for marker, contents in self.fields(files) if marker == key]

    def raw(self, files):
        if files is None: files = self._files
        elif isinstance(files, basestring): files = [files]
        return concat([self.open(f).read() for f in files])

    #{ Deprecated since 0.8
    @deprecated("Use .xml() instead.")
    def dictionary(self, files=None):
        raise ValueError("no longer supported -- use .xml() instead")
    @deprecated("Use .xml() instead.")
    def parse_corpus(self, files=None, key=None):
        return self.xml(items, key)
    #}
    
def demo():
    pass
    
if __name__ == '__main__':
    demo()
