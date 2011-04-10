# Natural Language Toolkit: Plaintext Corpus Reader
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Nitin Madnani <nmadnani@umiacs.umd.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for corpora that consist of plaintext documents.
"""

import codecs

import nltk.data
from nltk.tokenize import *

from util import *
from api import *

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
    
    def __init__(self, root, fileids, 
                 word_tokenizer=WordPunctTokenizer(),
                 sent_tokenizer=nltk.data.LazyLoader(
                     'tokenizers/punkt/english.pickle'),
                 para_block_reader=read_blankline_block,
                 encoding=None):
        """
        Construct a new plaintext corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = PlaintextCorpusReader(root, '.*\.txt')
        
        @param root: The root directory for this corpus.
        @param fileids: A list or regexp specifying the fileids in this corpus.
        @param word_tokenizer: Tokenizer for breaking sentences or
            paragraphs into words.
        @param sent_tokenizer: Tokenizer for breaking paragraphs
            into words.
        @param para_block_reader: The block reader used to divide the
            corpus into paragraph blocks.
        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader

    def raw(self, fileids=None, sourced=False):
        """
        @return: the given file(s) as a single string.
        @rtype: C{str}
        """
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f, sourced).read() for f in fileids])
    
    def words(self, fileids=None, sourced=False):
        """
        @return: the given file(s) as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        # Once we require Python 2.5, use source=(fileid if sourced else None)
        if sourced:
            return concat([self.CorpusView(path, self._read_word_block,
                                           encoding=enc, source=fileid)
                           for (path, enc, fileid)
                           in self.abspaths(fileids, True, True)])
        else:
            return concat([self.CorpusView(path, self._read_word_block,
                                           encoding=enc)
                           for (path, enc, fileid)
                           in self.abspaths(fileids, True, True)])
            
    
    def sents(self, fileids=None, sourced=False):
        """
        @return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        if self._sent_tokenizer is None:
            raise ValueError('No sentence tokenizer for this corpus')
        if sourced:
            return concat([self.CorpusView(path, self._read_sent_block,
                                           encoding=enc, source=fileid)
                           for (path, enc, fileid)
                           in self.abspaths(fileids, True, True)])
        else:
            return concat([self.CorpusView(path, self._read_sent_block,
                                           encoding=enc)
                           for (path, enc, fileid)
                           in self.abspaths(fileids, True, True)])
            

    def paras(self, fileids=None, sourced=False):
        """
        @return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        if self._sent_tokenizer is None:
            raise ValueError('No sentence tokenizer for this corpus')
        if sourced:
            return concat([self.CorpusView(path, self._read_para_block,
                                           encoding=enc, source=fileid)
                           for (path, enc, fileid)
                           in self.abspaths(fileids, True, True)])
        else:
            return concat([self.CorpusView(path, self._read_para_block,
                                           encoding=enc)
                           for (path, enc, fileid)
                           in self.abspaths(fileids, True, True)])

    def _read_word_block(self, stream):
        words = []
        for i in range(20): # Read 20 lines at a time.
            words.extend(self._word_tokenizer.tokenize(stream.readline()))
        return words
    
    def _read_sent_block(self, stream):
        sents = []
        for para in self._para_block_reader(stream):
            sents.extend([self._word_tokenizer.tokenize(sent)
                          for sent in self._sent_tokenizer.tokenize(para)])
        return sents
    
    def _read_para_block(self, stream):
        paras = []
        for para in self._para_block_reader(stream):
            paras.append([self._word_tokenizer.tokenize(sent)
                          for sent in self._sent_tokenizer.tokenize(para)])
        return paras
            

class CategorizedPlaintextCorpusReader(CategorizedCorpusReader,
                                    PlaintextCorpusReader):
    """
    A reader for plaintext corpora whose documents are divided into
    categories based on their file identifiers.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize the corpus reader.  Categorization arguments
        (C{cat_pattern}, C{cat_map}, and C{cat_file}) are passed to
        the L{CategorizedCorpusReader constructor
        <CategorizedCorpusReader.__init__>}.  The remaining arguments
        are passed to the L{PlaintextCorpusReader constructor
        <PlaintextCorpusReader.__init__>}.
        """
        CategorizedCorpusReader.__init__(self, kwargs)
        PlaintextCorpusReader.__init__(self, *args, **kwargs)

    def _resolve(self, fileids, categories):
        if fileids is not None and categories is not None:
            raise ValueError('Specify fileids or categories, not both')
        if categories is not None:
            return self.fileids(categories)
        else:
            return fileids
    def raw(self, fileids=None, categories=None):
        return PlaintextCorpusReader.raw(
            self, self._resolve(fileids, categories))
    def words(self, fileids=None, categories=None):
        return PlaintextCorpusReader.words(
            self, self._resolve(fileids, categories))
    def sents(self, fileids=None, categories=None):
        return PlaintextCorpusReader.sents(
            self, self._resolve(fileids, categories))
    def paras(self, fileids=None, categories=None):
        return PlaintextCorpusReader.paras(
            self, self._resolve(fileids, categories))

# is there a better way?
class PortugueseCategorizedPlaintextCorpusReader(CategorizedPlaintextCorpusReader):
    def __init__(self, *args, **kwargs):
        CategorizedCorpusReader.__init__(self, kwargs)
        kwargs['sent_tokenizer'] = nltk.data.LazyLoader('tokenizers/punkt/portuguese.pickle')
        PlaintextCorpusReader.__init__(self, *args, **kwargs)

class EuroparlCorpusReader(PlaintextCorpusReader):

    """
    Reader for Europarl corpora that consist of plaintext documents.  
    Documents are divided into chapters instead of paragraphs as
    for regular plaintext documents. Chapters are separated using blank
    lines. Everything is inherited from L{PlaintextCorpusReader} except 
    that:
      - Since the corpus is pre-processed and pre-tokenized, the
        word tokenizer should just split the line at whitespaces.
      - For the same reason, the sentence tokenizer should just
        split the paragraph at line breaks.
      - There is a new 'chapters()' method that returns chapters instead
        instead of paragraphs. 
      - The 'paras()' method inherited from PlaintextCorpusReader is
        made non-functional to remove any confusion between chapters
        and paragraphs for Europarl. 
    """

    def _read_word_block(self, stream):
        words = []
        for i in range(20): # Read 20 lines at a time.
            words.extend(stream.readline().split())
        return words

    def _read_sent_block(self, stream):
        sents = []
        for para in self._para_block_reader(stream):
            sents.extend([sent.split() for sent in para.splitlines()])
        return sents

    def _read_para_block(self, stream):
        paras = []
        for para in self._para_block_reader(stream):
            paras.append([sent.split() for sent in para.splitlines()])
        return paras

    def chapters(self, fileids=None):
        """
        @return: the given file(s) as a list of
            chapters, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        return concat([self.CorpusView(fileid, self._read_para_block,
                                       encoding=enc)
                       for (fileid, enc) in self.abspaths(fileids, True)])
                       
    def paras(self, fileids=None):
        raise NotImplementedError('The Europarl corpus reader does not support paragraphs. Please use chapters() instead.')

