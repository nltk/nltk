# Natural Language Toolkit: API for Corpus Readers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
API for corpus readers.
"""

class CorpusReader(object):
    """
    Generally constructed from a path & a list of items..

    Reader functions take a list of items, specifying which document
    or documents to return.  The value of C{items} can be a single
    filename; a list of filenames; or a stream.  If no items are
    specified, then a default list of documents will be used.
    """
    def __repr__(self):
        if hasattr(self, '_root'):
            return '<%s in %r>' % (self.__class__.__name__, self._root)
        else:
            return '<%s>' % (self.__class__.__name__)
