# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Penn Treebank corpus sample: tagged, NP-chunked, and parsed data from
Wall Street Journal for 3700 sentences.

This is a ~10% fragment of the Wall Street Journal section of the Penn
Treebank, (C) LDC 1995.  It is distributed with the Natural Language
Toolkit under the terms of the Creative Commons
Attribution-NonCommercial-ShareAlike License
[http://creativecommons.org/licenses/by-nc-sa/2.5/].
"""
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader
from nltk.corpus.reader.chunked import ChunkedCorpusReader
from nltk.tokenize import *
from nltk.tree import Tree
from nltk import chunk
import os.path, re
from nltk.utilities import deprecated

class TreebankCorpusReader(SyntaxCorpusReader):
    """
    Corpus reader for the Penn Treebank.  Combines three underlying formats:
    parsed, tagged+chunked, and plaintext.  Each of these formats is
    stored in a different subdirectory (combined/, tagged/, and raw/,
    respectively).

    If your corpus doesn't have this format, but just contains files
    with treebank-style parses, you should use
    L{BracketParseCorpusReader} instead.
    """
    def __init__(self, root):
        self._mrg_reader = BracketParseCorpusReader(
            os.path.join(root, 'combined'), '.*\.mrg')
        self._pos_reader = ChunkedCorpusReader(
            os.path.join(root, 'tagged'), '.*\.pos',
            sent_tokenizer=RegexpTokenizer(self._CHUNK_SENT_RE, gaps=True),
            para_block_reader=tagged_treebank_para_block_reader)

        # Make sure we have a consistent set of documents:
        documents = set(f[:-4] for f in self._mrg_reader.files())
        if set(f[:-4] for f in self._pos_reader.files()) != documents:
            raise ValueError('Documents in "combined" and "tagged" '
                             'subdirectories do not match.')
        for document in documents:
            if not os.path.exists(os.path.join(root, 'raw', document)):
                raise ValueError('File %r missing from "raw" subdirectory'
                                 % document)
        
        files = sorted(['combined/%s.mrg' % doc for doc in documents] +
                       ['tagged/%s.pos' % doc for doc in documents] +
                       ['raw/%s' % doc for doc in documents])
        CorpusReader.__init__(self, root, files)
        self._documents = tuple(sorted(documents))
        

    _CHUNK_SENT_RE = r'(?<=/\.)\s*(?![^\[]*\])'
    """Regexp that matches sentence boundaries in chunked ('.pos')
       files.  It searches for any token whose tag is '.', and then
       places a sentence bounary at the space after that token,
       *unless* the token is within a chunk."""
    
    def documents(self, files=None):
        """
        Return a list of document identifiers for all documents in
        this corpus, or for the documents with the given file(s) if
        specified.
        """
        if files is None:
            return self._documents
        if isinstance(files, basestring):
            files = [files]
        for f in files:
            if f not in self._files:
                raise KeyError('File id %s not found' % files)
        # File id -> document id
        return sorted(set([re.sub(r'\w+/([^.]*)(\.mrg|\.pos)?', r'\1', f)
                           for f in files]))

    def files(self, documents=None):
        """
        Return a list of file identifiers for the files that make up
        this corpus, or that store the given document(s) if specified.
        """
        if documents is None:
            return self._files
        elif isinstance(documents, basestring):
            documents = [documents]
        return sorted(set(['combined/%s.mrg' % doc for doc in documents] +
                          ['tagged/%s.pos' % doc for doc in documents] +
                          ['raw/%s' % doc for doc in documents]))

    def _getfiles(self, documents, subcorpus):
        """
        Helper that selects the appropraite files for a given set of
        documents from a given subcorpus (pos, mrg, or raw).
        """
        if documents is None:
            documents = self._documents
        else:
            if isinstance(documents, basestring):
                documents = [documents]
            for document in documents:
                if document not in self._documents:
                    if (document.startswith('tagged/') or
                        document.startswith('combined/') or
                        document.startswith('raw/')):
                        raise ValueError(
                            'Expected a document identifier, not a file '
                            'identifier.  (Use corpus.documents() to get '
                            'a list of document identifiers.')
                    else:
                        raise ValueError('Document identifier %s not found'
                                         % document)
        return ['%s.%s' % (d, subcorpus) for d in documents]

    # Delegate to one of our two sub-readers:
    def words(self, documents=None):
        return self._pos_reader.words(self._getfiles(documents, 'pos'))
    def sents(self, documents=None):
        return self._pos_reader.sents(self._getfiles(documents, 'pos'))
    def paras(self, documents=None):
        return self._pos_reader.paras(self._getfiles(documents, 'pos'))
    def tagged_words(self, documents=None):
        return self._pos_reader.tagged_words(self._getfiles(documents, 'pos'))
    def tagged_sents(self, documents=None):
        return self._pos_reader.tagged_sents(self._getfiles(documents, 'pos'))
    def tagged_paras(self, documents=None):
        return self._pos_reader.tagged_paras(self._getfiles(documents, 'pos'))
    def chunked_words(self, documents=None):
        return self._pos_reader.chunked_words(self._getfiles(documents, 'pos'))
    def chunked_sents(self, documents=None):
        return self._pos_reader.chunked_sents(self._getfiles(documents, 'pos'))
    def chunked_paras(self, documents=None):
        return self._pos_reader.chunked_paras(self._getfiles(documents, 'pos'))
    def parsed_sents(self, documents=None):
        return self._mrg_reader.parsed_sents(self._getfiles(documents, 'mrg'))

    # Read in the text file, and strip the .START prefix.
    def text(self, documents=None):
        if documents is None: documents = self._documents
        filenames = [os.path.join(self._root, 'raw', d) for d in documents]
        return concat([re.sub(r'\A\s*\.START\s*', '', open(filename).read())
                       for filename in filenames])

    #{ Deprecated since 0.9.1
    @deprecated("Use corpus.documents() instead")
    def _get_items(self): return self.documents()
    items = property(_get_items)
    #}
    
    #{ Deprecated since 0.8
    @deprecated("Use .text() or .sents() or .tagged_sents() or "
                ".parsed_sents() instead.")
    def read(self, documents=None, format='parsed'):
        if format == 'parsed': return self.parsed_sents(documents)
        if format == 'raw': return self.text(documents)
        if format == 'tokenized': return self.sents(documents)
        if format == 'tagged': return self.tagged_sents(documents)
        if format == 'parsed_no_pos': raise ValueError('no longer supported')
        raise ValueError('bad format %r' % format)
    @deprecated("Use .parsed_sents() instead.")
    def parsed(self, items=None):
        return self.parsed_sents(items)
    @deprecated("Use .sents() instead.")
    def tokenized(self, items=None):
        return self.sents(items)
    @deprecated("Use .tagged_sents() instead.")
    def tagged(self, items=None):
        return self.tagged_sents(items)
    @deprecated("Operation no longer supported -- use .parsed_sents().")
    def parsed_no_pos(self, itemns=None):
        raise ValueError('format "parsed_no_pos" no longer supported')
    #}
    
def tagged_treebank_para_block_reader(stream):
    # Read the next paragraph.
    para = ''
    while True:
        line = stream.readline()
        # End of paragraph:
        if re.match('======+\s*$', line):
            if para.strip(): return [para]
        # End of file:
        elif line == '':
            if para.strip(): return [para]
            else: return []
        # Content line:
        else:
            para += line
            
