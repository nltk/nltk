# Natural Language Toolkit: Tagged Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A reader for corpora whose documents contain part-of-speech-tagged words.
"""       

from api import *
from util import *
from nltk.tag import str2tuple
from nltk.tokenize import *
import os
from nltk.internals import deprecated

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
    def __init__(self, root, files, 
                 sep='/', word_tokenizer=WhitespaceTokenizer(),
                 sent_tokenizer=RegexpTokenizer('\n', gaps=True),
                 para_block_reader=read_blankline_block):
        """
        Construct a new Tagged Corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = TaggedCorpusReader(root, '.*', '.txt')
        
        @param root: The root directory for this corpus.
        @param files: A list or regexp specifying the files in this corpus.
        """
        CorpusReader.__init__(self, root, files)
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader

    def raw(self, files=None):
        """
        @return: the given file or files as a single string.
        @rtype: C{str}
        """
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

    def words(self, files=None):
        """
        @return: the given file or files as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        return concat([TaggedCorpusView(filename, False, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        """
        @return: the given file or files as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        return concat([TaggedCorpusView(filename, False, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self.abspaths(files)])

    def paras(self, files=None):
        """
        @return: the given file or files as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        return concat([TaggedCorpusView(filename, False, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self.abspaths(files)])

    def tagged_words(self, files=None):
        """
        @return: the given file or files as a list of tagged
            words and punctuation symbols, encoded as tuples
            C{(word,tag)}.
        @rtype: C{list} of C{(str,str)}
        """
        return concat([TaggedCorpusView(filename, True, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self.abspaths(files)])

    def tagged_sents(self, files=None):
        """
        @return: the given file or files as a list of
            sentences, each encoded as a list of C{(word,tag)} tuples.
            
        @rtype: C{list} of (C{list} of C{(str,str)})
        """
        return concat([TaggedCorpusView(filename, True, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self.abspaths(files)])

    def tagged_paras(self, files=None):
        """
        @return: the given file or files as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of C{(word,tag)} tuples.
        @rtype: C{list} of (C{list} of (C{list} of C{(str,str)}))
        """
        return concat([TaggedCorpusView(filename, True, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self.abspaths(files)])

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .words() or .sents() or .paras() or "
                ".tagged_words() or .tagged_sents() or .tagged_paras() "
                "instead.")
    def read(self, items=None, format='tagged', gs=True, gp=False):
        if format == 'tagged': return self.tagged(items, gs, gp)
        if format == 'tokenized': return self.tokenized(items, gs, gp)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .words() or .sents() or .paras() instead.")
    def tokenized(self, items=None, gs=True, gp=False):
        if gs and gp: return self.paras()
        elif gs and not gp: return self.sents()
        elif not gs and not gp: return self.words()
        else: return 'Operation no longer supported.'
    @deprecated("Use .tagged_words() or .tagged_sents() or "
                ".tagged_paras() instead.")
    def tagged(self, items=None, gs=True, gp=False):
        if gs and gp: return self.tagged_paras()
        elif gs and not gp: return self.tagged_sents()
        elif not gs and not gp: return self.tagged_words()
        else: return 'Operation no longer supported.'
    #}
    
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

    def _resolve(self, files, categories):
        if files is not None and categories is not None:
            raise ValueError('Specify files or categories, not both')
        if categories is not None:
            return self.files(categories)
        else:
            return files
    def raw(self, files=None, categories=None):
        return TaggedCorpusReader.raw(
            self, self._resolve(files, categories))
    def words(self, files=None, categories=None):
        return TaggedCorpusReader.words(
            self, self._resolve(files, categories))
    def sents(self, files=None, categories=None):
        return TaggedCorpusReader.sents(
            self, self._resolve(files, categories))
    def paras(self, files=None, categories=None):
        return TaggedCorpusReader.paras(
            self, self._resolve(files, categories))
    def tagged_words(self, files=None, categories=None):
        return TaggedCorpusReader.tagged_words(
            self, self._resolve(files, categories))
    def tagged_sents(self, files=None, categories=None):
        return TaggedCorpusReader.tagged_sents(
            self, self._resolve(files, categories))
    def tagged_paras(self, files=None, categories=None):
        return TaggedCorpusReader.tagged_paras(
            self, self._resolve(files, categories))

class TaggedCorpusView(StreamBackedCorpusView):
    """
    A specialized corpus view for tagged documents.  It can be
    customized via flags to divide the tagged corpus documents up by
    sentence or paragraph, and to include or omit part of speech tags.
    C{TaggedCorpusView} objects are typically created by
    L{TaggedCorpusReader} (not directly by nltk users).
    """
    def __init__(self, corpus_file, tagged, group_by_sent, group_by_para,
                 sep, word_tokenizer, sent_tokenizer, para_block_reader):
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader
        StreamBackedCorpusView.__init__(self, corpus_file)
        
    def read_block(self, stream):
        """Reads one paragraph at a time."""
        block = []
        for para_str in self._para_block_reader(stream):
            para = []
            for sent_str in self._sent_tokenizer.tokenize(para_str):
                sent = [str2tuple(s, self._sep) for s in
                        self._word_tokenizer.tokenize(sent_str)]
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

class MacMorphoCorpusReader(TaggedCorpusReader):
    """
    A corpus reader for the MAC_MORPHO corpus.  Each line contains a
    single tagged word, using '_' as a separator.  Sentence boundaries
    are based on the end-sentence tag ('_.').  Paragraph information
    is not included in the corpus, so each paragraph returned by
    L{self.paras()} and L{self.tagged_paras()} contains a single
    sentence.
    """
    def __init__(self, root, files):
        TaggedCorpusReader.__init__(
            self, root, files, sep='_',
            word_tokenizer=LineTokenizer(),
            sent_tokenizer=RegexpTokenizer('.*\n'),
            para_block_reader=self._read_block)

    def _read_block(self, stream):
        return read_regexp_block(stream, r'.*', r'.*_\.')
