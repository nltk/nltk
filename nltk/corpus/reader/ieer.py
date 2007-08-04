# Natural Language Toolkit: IEER Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus reader for the Information Extraction and Entity Recognition Corpus.

NIST 1999 Information Extraction: Entity Recognition Evaluation
http://www.itl.nist.gov/iad/894.01/tests/ie-er/er_99/er_99.htm

This corpus contains the NEWSWIRE development test data for the
NIST 1999 IE-ER Evaluation.  The files were taken from the
subdirectory: /ie_er_99/english/devtest/newswire/*.ref.nwt
and filenames were shortened.

The corpus contains the following files: APW_19980314, APW_19980424,
APW_19980429, NYT_19980315, NYT_19980403, and NYT_19980407.
"""

from util import *
from api import *
from nltk import chunk
import os

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
titles = {
    'APW_19980314': 'Associated Press Weekly, 14 March 1998',
    'APW_19980424': 'Associated Press Weekly, 24 April 1998',
    'APW_19980429': 'Associated Press Weekly, 29 April 1998',
    'NYT_19980315': 'New York Times, 15 March 1998',
    'NYT_19980403': 'New York Times, 3 April 1998',
    'NYT_19980407': 'New York Times, 7 April 1998',
    }

#: A list of all documents in this corpus.
items = sorted(titles)

class IEERDocument:
    def __init__(self, text, docno=None, doctype=None,
                 date_time=None, headline=None):
        self.text = text
        self.docno = docno
        self.doctype = doctype
        self.date_time = date_time
        self.headline = headline
    def __repr__(self):
        if self.headline:
            headline = ' '.join(self.headline.leaves())
        else:
            headline = ' '.join([w for w in self.text.leaves()
                                 if w[:1] != '<'][:12])+'...'
        if self.docno is not None:            
            return '<IEERDocument %s: %r>' % (self.docno, headline)
        else:
            return '<IEERDocument: %r>' % headline

class IEERCorpusReader(CorpusReader):
    """
    """
    def __init__(self, root, items, extension=''):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension
        
    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])
    
    def docs(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_block)
                       for filename in self._item_filenames(items)])
    
    def parsed_docs(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_parsed_block)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
    def _read_parsed_block(self,stream):
        return [self._parse(doc) for doc in self._read_block(stream)]

    def _parse(self, doc):
        val = chunk.ieerstr2tree(doc, top_node="DOCUMENT")
        if isinstance(val, dict):
            return IEERDocument(**val)
        else:
            return IEERDocument(val)
    
    def _read_block(self, stream):
        out = []
        # Skip any preamble.
        for line in stream:
            if line.strip() == '<DOC>': break
        # Read the document
        out.append(line)
        for line in stream:
            out.append(line)
            if line.strip() == '</DOC>': break
        # Return the document
        return ['\n'.join(out)]

    #{ Deprecated since 0.8
    from nltk.utilities import deprecated
    @deprecated("Use .parsed_docs() or .raw() or .docs() instead.")
    def read(items, format='parsed'):
        if format == 'parsed': return self.parsed_docs(items)
        if format == 'raw': return self.raw(items)
        if format == 'docs': return self.docs(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .parsed_docs() instead.")
    def parsed(items):
        return self.parsed_docs(items)
    #}
