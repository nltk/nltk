# Natural Language Toolkit: Plaintext Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A reader for corpora that consist of plaintext documents.
"""

import nltk.data
from nltk.tokenize import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.utilities import deprecated

class PlaintextCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of plaintext documents.  Paragraphs
    are assumed to be split using blank lines.  Sentences and words can
    be tokenized using the default tokenizers, or by custom tokenizers
    specificed as parameters to the constructor.

    This corpus reader can be customized (e.g., to skip preface
    sections of specific document formats) by creating a subclass and
    overriding the L{CorpusView} class variable.
    """

    CorpusView = StreamBackedCorpusView
    """The corpus view class used by this reader.  Subclasses of
       L{PlaintextCorpusReader} may specify alternative corpus view
       classes (e.g., to skip the preface sections of documents.)"""
    
    def __init__(self, root, documents, extension='', 
                 word_tokenizer=WordPunctTokenizer(),
                 sent_tokenizer=nltk.data.LazyLoader(
                     'tokenizers/punkt/english.pickle'),
                 para_block_reader=read_blankline_block, startpos=0):
        """
        Construct a new plaintext corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = PlaintextCorpusReader(root, '.*', '.txt')
        
        @param root: The root directory for this corpus.
        @param documents: A list of documents in this corpus.  This list can
            either be specified explicitly, as a list of strings; or
            implicitly, as a regular expression over file paths.  The
            filename for each item will be constructed by joining the
            reader's root to the filename, and adding the extension.
        @param extension: File extension for documents in this corpus.
            This extension will be concatenated to item names to form
            file names.  If C{documents} is specified as a regular
            expression, then the escaped extension will automatically
            be added to that regular expression.
        @param word_tokenizer: Tokenizer for breaking sentences or
            paragraphs into words.
        @param sent_tokenizer: Tokenizer for breaking paragraphs
            into words.
        """
        if not os.path.isdir(root):
            raise ValueError('Root directory %r not found!' % root)
        if isinstance(documents, basestring):
            documents = find_corpus_items(root, documents, extension)
        self._documents = tuple(documents)
        self._root = root
        self._extension = extension
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader

    def raw(self, documents=None, categories=None):
        """
        @return: the given document or documents as a single string.
        @rtype: C{str}
        """
        return concat([open(filename).read()
                       for filename in self.filenames(documents, categories)])
    
    def words(self, documents=None, categories=None):
        """
        @return: the given document or documents as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        return concat([self.CorpusView(filename, self._read_word_block)
                       for filename in self.filenames(documents, categories)])
    
    def sents(self, documents=None, categories=None):
        """
        @return: the given document or documents as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        if self._sent_tokenizer is None:
            raise ValueError('No sentence tokenizer for this corpus')
        return concat([self.CorpusView(filename, self._read_sent_block)
                       for filename in self.filenames(documents, categories)])

    def paras(self, documents=None, categories=None):
        """
        @return: the given document or documents as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        if self._sent_tokenizer is None:
            raise ValueError('No sentence tokenizer for this corpus')
        return concat([self.CorpusView(filename, self._read_para_block)
                       for filename in self.filenames(documents, categories)])

    def _read_word_block(self, stream):
        words = []
        for i in range(20): # Read 20 lines at a time.
            words.extend(self._word_tokenizer.tokenize(stream.readline()))
        return words
    
    def _read_sent_block(self, stream):
        sents = []
        for para in self._para_block_reader(stream):
            # [xx] remove the list() once tokenizers are changed to
            # return lists, not iterators.
            sents.extend([list(self._word_tokenizer.tokenize(sent))
                          for sent in self._sent_tokenizer.tokenize(para)])
        return sents
    
    def _read_para_block(self, stream):
        paras = []
        for para in self._para_block_reader(stream):
            # [xx] remove the list() once tokenizers are changed to
            # return lists, not iterators.
            paras.append([list(self._word_tokenizer.tokenize(sent))
                          for sent in self._sent_tokenizer.tokenize(para)])
        return paras
            
    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .words() instead.")
    def read(self, items=None, format='tokenized'):
        if format == 'raw': return self.raw(items)
        if format == 'tokenized': return self.words(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .words() instead.")
    def tokenized(self, items=None):
        return self.words(items)
    #}

class ListCategorizedPlaintextCorpusReader(ListCategorizedCorpus, PlaintextCorpusReader):
    
    def __init__(self, root, *args, **kwargs):
        catfile = kwargs['catfile']
        del kwargs['catfile']
        PlaintextCorpusReader.__init__(self, root, *args, **kwargs)
        ListCategorizedCorpus.__init__(self, root, catfile)

class LocationCategorizedPlaintextCorpusReader(LocationCategorizedCorpus, PlaintextCorpusReader):
    
    def __init__(self, root, *args, **kwargs):
        pattern = kwargs['pattern']
        del kwargs['pattern']
        PlaintextCorpusReader.__init__(self, root, *args, **kwargs)
        LocationCategorizedCorpus.__init__(self, pattern)


