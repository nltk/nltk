# Natural Language Toolkit: IEER Corpus Reader
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
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

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk import chunk
import codecs
from nltk.internals import deprecated

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
documents = sorted(titles)

class IEERDocument:
    def __init__(self, text, docno=None, doctype=None,
                 date_time=None, headline=''):
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
    def raw(self, files=None):
        if files is None: files = self._files
        elif isinstance(files, basestring): files = [files]
        return concat([self.open(f).read() for f in files])

    def docs(self, files=None):
        return concat([StreamBackedCorpusView(filename, self._read_block,
                                              encoding=enc)
                       for (filename, enc) in self.abspaths(files, True)])
    
    def parsed_docs(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_parsed_block,
                                              encoding=enc)
                       for (filename, enc) in self.abspaths(files, True)])

    def _read_parsed_block(self,stream):
        # TODO: figure out while empty documents are being returned
        return [self._parse(doc) for doc in self._read_block(stream)
                if self._parse(doc).docno is not None]
  
    def _parse(self, doc):
        val = chunk.ieerstr2tree(doc, top_node="DOCUMENT")
        if isinstance(val, dict):
            return IEERDocument(**val)
        else:
            return IEERDocument(val)
     
    def _read_block(self, stream):
        out = []
        # Skip any preamble.
        while True:
            line = stream.readline()
            if not line: break
            if line.strip() == '<DOC>': break
        out.append(line)
        # Read the document
        while True:
            line = stream.readline()
            if not line: break
            out.append(line)
            if line.strip() == '</DOC>': break
        # Return the document
        return ['\n'.join(out)]

    #{ Deprecated since 0.8
    @deprecated("Use .parsed_docs() or .raw() or .docs() instead.")
    def read(self, items, format='parsed'):
        if format == 'parsed': return self.parsed_docs(items)
        if format == 'raw': return self.raw(items)
        if format == 'docs': return self.docs(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .parsed_docs() instead.")
    def parsed(self, items):
        return self.parsed_docs(items)
    #}

