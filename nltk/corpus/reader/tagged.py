# Natural Language Toolkit: Tagged Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A reader for corpora whose documents contain part-of-speech-tagged
words.
"""       

from api import *
from util import *
from nltk.tag import tag2tuple
from nltk.tokenize import *
import os

class TaggedCorpusReader(CorpusReader):
    """
    Reader for simple part-of-speech tagged corpora.  Paragraphs are
    assumed to be split using blank lines.  Sentences and words can be
    tokenized using the default tokenizers, or by custom tokenizers
    specificed as parameters to the constructor.  Words are parsed
    using L{nltk.tag.tag2tuple}.  By default, C{'/'} is used as the
    separator.  I.e., words should have the form::

       word1/tag1 word2/tag2 word3/tag3 ...

    But custom separators may be specified as parameters to the
    constructor.  Part of speech tags are case-normalized to upper
    case.
    """
    def __init__(self, root, items, extension='',
                 sep='/', word_tokenizer=WhitespaceTokenizer(),
                 sent_tokenizer=RegexpTokenizer('\n', gaps=True),
                 para_block_reader=read_blankline_block):
        """
        Construct a new Tagged Corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = TaggedCorpusReader(root, '.*', '.txt')
        
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.  This list can
            either be specified explicitly, as a list of strings; or
            implicitly, as a regular expression over file paths.  The
            filename for each item will be constructed by joining the
            reader's root to the filename, and adding the extension.
        @param extension: File extension for items in this corpus.
            This extension will be concatenated to item names to form
            file names.  If C{items} is specified as a regular
            expression, then the escaped extension will automatically
            be added to that regular expression.
        """
        if not os.path.isdir(root):
            raise ValueError('Root directory %r not found!' % root)
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._items = tuple(items)
        self._root = root
        self._extension = extension
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader

    root = property(lambda self: self._root, doc="""
        The directory where this corpus is stored..""")

    items = property(lambda self: self._items, doc="""
        A list of the documents in this corpus""")
    
    def raw(self, items=None):
        """
        @return: the given document or documents as a single string.
        @rtype: C{str}
        """
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def words(self, items=None):
        """
        @return: the given document or documents as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        return concat([TaggedCorpusView(filename, False, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        """
        @return: the given document or documents as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        return concat([TaggedCorpusView(filename, False, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self._item_filenames(items)])

    def paras(self, items=None):
        """
        @return: the given document or documents as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        return concat([TaggedCorpusView(filename, False, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self._item_filenames(items)])

    def tagged_words(self, items=None):
        """
        @return: the given document or documents as a list of tagged
            words and punctuation symbols, encoded as tuples
            C{(word,tag)}.
        @rtype: C{list} of C{(str,str)}
        """
        return concat([TaggedCorpusView(filename, True, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        """
        @return: the given document or documents as a list of
            sentences, each encoded as a list of C{(word,tag)} tuples.
            
        @rtype: C{list} of (C{list} of C{(str,str)})
        """
        return concat([TaggedCorpusView(filename, True, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self._item_filenames(items)])

    def tagged_paras(self, items=None):
        """
        @return: the given document or documents as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of C{(word,tag)} tuples.
        @rtype: C{list} of (C{list} of (C{list} of C{(str,str)}))
        """
        return concat([TaggedCorpusView(filename, True, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer,
                                        self._para_block_reader)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
    #{ Deprecated since 0.8
    from nltk.utilities import deprecated
    @deprecated("Use .raw() or .words() or .sents() or .paras() or "
                ".tagged_words() or .tagged_sents() or .tagged_paras() "
                "instead.")
    def read(items=None, format='tagged', gs=True, gp=True):
        if format == 'tagged': return self.tagged(items, gs, gp)
        if format == 'tokenized': return self.tokenized(items, gs, gp)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .words() or .sents() or .paras() instead.")
    def tokenized(items=None, gs=True, gp=True):
        if gs and gp: return self.paras()
        elif gs and not gp: return self.sents()
        elif not gs and not gp: return self.words()
        else: return 'Operation no longer supported.'
    @deprecated("Use .tagged_words() or .tagged_sents() or "
                ".tagged_paras() instead.")
    def tagged(items=None, gs=True, gp=True):
        if gs and gp: return self.tagged_paras()
        elif gs and not gp: return self.tagged_sents()
        elif not gs and not gp: return self.tagged_words()
        else: return 'Operation no longer supported.'
    #}
    
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
                sent = [tag2tuple(w) for w in
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

