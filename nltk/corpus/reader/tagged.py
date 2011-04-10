# Natural Language Toolkit: Tagged Corpus Reader
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
#         Jacob Perkins <japerk@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for corpora whose documents contain part-of-speech-tagged words.
"""       

import os

from nltk.tag import str2tuple
from nltk.tokenize import *

from api import *
from util import *
from timit import read_timit_block

class TaggedCorpusReader(CorpusReader):
    """
    Reader for simple part-of-speech tagged corpora.  Paragraphs are
    assumed to be split using blank lines.  Sentences and words can be
    tokenized using the default tokenizers, or by custom tokenizers
    specified as parameters to the constructor.  Words are parsed
    using L{nltk.tag.str2tuple}.  By default, C{'/'} is used as the
    separator.  I.e., words should have the form::

       word1/tag1 word2/tag2 word3/tag3 ...

    But custom separators may be specified as parameters to the
    constructor.  Part of speech tags are case-normalized to upper
    case.
    """
    def __init__(self, root, fileids, 
                 sep='/', word_tokenizer=WhitespaceTokenizer(),
                 sent_tokenizer=RegexpTokenizer('\n', gaps=True),
                 para_block_reader=read_blankline_block,
                 encoding=None,
                 tag_mapping_function=None):
        """
        Construct a new Tagged Corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = TaggedCorpusReader(root, '.*', '.txt')
        
        @param root: The root directory for this corpus.
        @param fileids: A list or regexp specifying the fileids in this corpus.
        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader
        self._tag_mapping_function = tag_mapping_function

    def raw(self, fileids=None):
        """
        @return: the given file(s) as a single string.
        @rtype: C{str}
        """
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])

    def words(self, fileids=None):
        """
        @return: the given file(s) as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        return concat([TaggedCorpusView(fileid, enc,
                                        False, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader,
                                        None)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def sents(self, fileids=None):
        """
        @return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        return concat([TaggedCorpusView(fileid, enc,
                                        False, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader,
                                        None)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def paras(self, fileids=None):
        """
        @return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        return concat([TaggedCorpusView(fileid, enc,
                                        False, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader,
                                        None)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def tagged_words(self, fileids=None, simplify_tags=False):
        """
        @return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            C{(word,tag)}.
        @rtype: C{list} of C{(str,str)}
        """
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([TaggedCorpusView(fileid, enc,
                                        True, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader,
                                        tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def tagged_sents(self, fileids=None, simplify_tags=False):
        """
        @return: the given file(s) as a list of
            sentences, each encoded as a list of C{(word,tag)} tuples.
            
        @rtype: C{list} of (C{list} of C{(str,str)})
        """
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([TaggedCorpusView(fileid, enc,
                                        True, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader,
                                        tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def tagged_paras(self, fileids=None, simplify_tags=False):
        """
        @return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of C{(word,tag)} tuples.
        @rtype: C{list} of (C{list} of (C{list} of C{(str,str)}))
        """
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([TaggedCorpusView(fileid, enc,
                                        True, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader,
                                        tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])

class CategorizedTaggedCorpusReader(CategorizedCorpusReader,
                                    TaggedCorpusReader):
    """
    A reader for part-of-speech tagged corpora whose documents are
    divided into categories based on their file identifiers.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize the corpus reader.  Categorization arguments
        (C{cat_pattern}, C{cat_map}, and C{cat_file}) are passed to
        the L{CategorizedCorpusReader constructor
        <CategorizedCorpusReader.__init__>}.  The remaining arguments
        are passed to the L{TaggedCorpusReader constructor
        <TaggedCorpusReader.__init__>}.
        """
        CategorizedCorpusReader.__init__(self, kwargs)
        TaggedCorpusReader.__init__(self, *args, **kwargs)

    def _resolve(self, fileids, categories):
        if fileids is not None and categories is not None:
            raise ValueError('Specify fileids or categories, not both')
        if categories is not None:
            return self.fileids(categories)
        else:
            return fileids
    def raw(self, fileids=None, categories=None):
        return TaggedCorpusReader.raw(
            self, self._resolve(fileids, categories))
    def words(self, fileids=None, categories=None):
        return TaggedCorpusReader.words(
            self, self._resolve(fileids, categories))
    def sents(self, fileids=None, categories=None):
        return TaggedCorpusReader.sents(
            self, self._resolve(fileids, categories))
    def paras(self, fileids=None, categories=None):
        return TaggedCorpusReader.paras(
            self, self._resolve(fileids, categories))
    def tagged_words(self, fileids=None, categories=None, simplify_tags=False):
        return TaggedCorpusReader.tagged_words(
            self, self._resolve(fileids, categories), simplify_tags)
    def tagged_sents(self, fileids=None, categories=None, simplify_tags=False):
        return TaggedCorpusReader.tagged_sents(
            self, self._resolve(fileids, categories), simplify_tags)
    def tagged_paras(self, fileids=None, categories=None, simplify_tags=False):
        return TaggedCorpusReader.tagged_paras(
            self, self._resolve(fileids, categories), simplify_tags)

class TaggedCorpusView(StreamBackedCorpusView):
    """
    A specialized corpus view for tagged documents.  It can be
    customized via flags to divide the tagged corpus documents up by
    sentence or paragraph, and to include or omit part of speech tags.
    C{TaggedCorpusView} objects are typically created by
    L{TaggedCorpusReader} (not directly by nltk users).
    """
    def __init__(self, corpus_file, encoding, tagged, group_by_sent,
                 group_by_para, sep, word_tokenizer, sent_tokenizer,
                 para_block_reader, tag_mapping_function=None):
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader
        self._tag_mapping_function = tag_mapping_function
        StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)
        
    def read_block(self, stream):
        """Reads one paragraph at a time."""
        block = []
        for para_str in self._para_block_reader(stream):
            para = []
            for sent_str in self._sent_tokenizer.tokenize(para_str):
                sent = [str2tuple(s, self._sep) for s in
                        self._word_tokenizer.tokenize(sent_str)]
                if self._tag_mapping_function:
                    sent = [(w, self._tag_mapping_function(t)) for (w,t) in sent]
                if not self._tagged:
                    sent = [w for (w,t) in sent]
                if self._group_by_sent:
                    para.append(sent)
                else:
                    para.extend(sent)
            if self._group_by_para:
                block.append(para)
            else:
                block.extend(para)
        return block

# needs to implement simplified tags
class MacMorphoCorpusReader(TaggedCorpusReader):
    """
    A corpus reader for the MAC_MORPHO corpus.  Each line contains a
    single tagged word, using '_' as a separator.  Sentence boundaries
    are based on the end-sentence tag ('_.').  Paragraph information
    is not included in the corpus, so each paragraph returned by
    L{self.paras()} and L{self.tagged_paras()} contains a single
    sentence.
    """
    def __init__(self, root, fileids, encoding=None, tag_mapping_function=None):
        TaggedCorpusReader.__init__(
            self, root, fileids, sep='_',
            word_tokenizer=LineTokenizer(),
            sent_tokenizer=RegexpTokenizer('.*\n'),
            para_block_reader=self._read_block,
            encoding=encoding,
            tag_mapping_function=tag_mapping_function)

    def _read_block(self, stream):
        return read_regexp_block(stream, r'.*', r'.*_\.')

class TimitTaggedCorpusReader(TaggedCorpusReader):
    """
    A corpus reader for tagged sentences that are included in the TIMIT corpus.
    """
    def __init__(self, *args, **kwargs):
        TaggedCorpusReader.__init__(
            self, para_block_reader=read_timit_block, *args, **kwargs)
    
    def paras(self):
        raise NotImplementedError('use sents() instead')
    
    def tagged_paras(self):
        raise NotImplementedError('use tagged_sents() instead')