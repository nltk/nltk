# Natural Language Toolkit: XML Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus reader for corpora whose documents are xml files.

(note -- not named 'xml' to avoid conflicting w/ standard xml package)
"""

from api import CorpusReader
from util import *
from nltk.internals import deprecated

# Use the c version of ElementTree, which is faster, if possible:
try: from xml.etree import cElementTree as ElementTree
except ImportError: from nltk.etree import ElementTree

class XMLCorpusReader(CorpusReader):
    """
    Corpus reader for corpora whose documents are xml files.
    """
    def xml(self, files=None):
        return concat([ElementTree.parse(filename).getroot()
                       for filename in self.abspaths(files)])

    def raw(self, files=None):
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .xml() instead.")
    def read(self, items=None, format='xml'):
        if format == 'raw': return self.raw(items)
        if format == 'xml': return self.xml(items)
        raise ValueError('bad format %r' % format)
    #}
