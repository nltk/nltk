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
from nltk.etree import ElementTree
from nltk.utilities import deprecated

class XMLCorpusReader(CorpusReader):
    """
    Corpus reader for corpora whose documents are xml files.
    """
    def __init__(self, root, documents, extension='.xml'):
        """
        @param root: The root directory for this corpus.
        @param documents: A list of documents in this corpus.
        @param extension: File extension for documents in this corpus.
        """
        if isinstance(documents, basestring):
            documents = find_corpus_items(root, documents, extension)
        self._root = root
        self._documents = tuple(documents)
        self._extension = extension

    def xml(self, documents=None):
        return concat([ElementTree.parse(filename).getroot()
                       for filename in self.filenames(documents)])

    def raw(self, documents=None):
        return concat([open(filename).read()
                       for filename in self.filenames(documents)])

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .xml() instead.")
    def read(self, items=None, format='xml'):
        if format == 'raw': return self.raw(items)
        if format == 'xml': return self.xml(items)
        raise ValueError('bad format %r' % format)
    #}
