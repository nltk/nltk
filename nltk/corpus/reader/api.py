# Natural Language Toolkit: API for Corpus Readers
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
API for corpus readers.
"""

import os, re
from nltk import defaultdict

class CorpusReader(object):
    """
    Generally constructed from a path & a list of documents.

    Reader functions take a list of documents, specifying which document
    or documents to return.  The value of C{documents} can be a single
    document; a list of documents; or a stream.  If no documents are
    specified, then a default list of documents will be used.
    """
    def __repr__(self):
        if hasattr(self, '_root'):
            return '<%s in %r>' % (self.__class__.__name__, self._root)
        else:
            return '<%s>' % (self.__class__.__name__)

    root = property(lambda self: self._root, doc="""
        The directory where this corpus is stored.""")

    items = property(lambda self: self._documents, doc="""
        A list of the documents in this corpus (deprecated, use documents() instead).""")
    
    def documents(self):
        """
        @return: the list of documents in this corpus
        @rtype: C{list}
        """
        return self._documents

    def filenames(self, documents=None, categories=None):
        """
        @param documents: The individual documents
        @type documents: C{str} or C{list}
        @param categories: The categories of documents
        @type categories: C{str} or C{list}
        @return: the list of filenames in this corpus, for the specified documents or categories
        @rtype: C{list}
        """
        assert not(documents and categories), "Must not specify both documents and categories"
        if categories:
            if isinstance(categories, basestring): categories = [categories]
            return list(reduce(set.union, [self.filenames(documents=self.documents(category)) for category in categories]))
        if documents is None: documents = self.documents()
        if isinstance(documents, basestring): documents = [documents]            
        return [os.path.join(self._root, '%s%s' % (document, self._extension)) for document in documents]        


######################################################################
#{ Corpora containing categorized items
######################################################################

class CategorizedCorpus(object):
    """Parent class for categorized corpora, allowing us to map between
    corpus categories and corpus documents (two-way dict).  Derived classes use
    locally-defined methods to populate the defaultdicts used by this class."""
    
    def __init__(self):
        self._d2c = {}   # document to category mapping
        self._c2d = {}   # category to document mapping

    def categories(self, documents=None):
        """List the categories defined for the corpus, or for the document if it is given."""
        if documents:
            if isinstance(documents, basestring): documents = [documents]
            return sorted(reduce(set.union, [self._d2c[document] for document in documents]))
        else:
            try:
                return self._categories
            except AttributeError:
                self._categories = sorted(self._c2d.keys())
                return self._categories  # cache the categories
    
    def documents(self, categories=None):
        """List the documents of the corpus, or the documents of the given category."""
        if categories:
            if isinstance(categories, basestring): categories = [categories]
            return sorted(reduce(set.union, [self._c2d[category] for category in categories]))
        else:
            return self._documents

    def _add(self, document, category):
        """Add the document of the given category to the dictionaries."""
        if document not in self._d2c:
            self._d2c[document] = set()
        if category not in self._c2d:
            self._c2d[category] = set()
        self._d2c[document].add(category)
        self._c2d[category].add(document)

class LocationCategorizedCorpus(CategorizedCorpus):
    """Corpora whose documents are categorized by the location (file or directory names).
    E.g. for Brown: pattern = "c(\a)\d\d", e.g. ca01 -> a
    E.g. for QC: pattern = "(.*)/.*"
    """

    def __init__(self, pattern):
        """pattern is applied to each document and its matching segment is the category"""
        CategorizedCorpus.__init__(self)
        for document in self.documents():
             category = re.match(pattern, document).group(1)
             self._add(document, category)
        
class ListCategorizedCorpus(CategorizedCorpus):
    """Corpora whose documents are categorized by a list, e.g. Reuters"""

    def __init__(self, root, catfile, delimiter=" "):
        """each line of the category file identifies a document and one or more categories."""
        CategorizedCorpus.__init__(self)
        for line in open(os.path.join(root, catfile)).readlines():
            line = line.strip()
            document, categories = line.split(delimiter, 1)
            for category in categories.split(delimiter):
                self._add(document, category)
