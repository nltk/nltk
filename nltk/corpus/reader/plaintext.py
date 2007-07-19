# Natural Language Toolkit: Plaintext Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A reader for corpora that consist of plaintext documents.
"""

from nltk import tokenize
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *

class PlaintextCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of plaintext documents.  Paragraphs
    are assumed to be split using blank lines.  Sentences and words can
    be tokenized using the default tokenizers, or by custom tokenizers
    specificed as parameters to the constructor.
    """

    CorpusView = StreamBackedCorpusView
    """The corpus view class used by this reader.  Subclasses may
       specify alternative corpus view classes (e.g., to skip the
       preface sections of documents.)"""
    
    def __init__(self, root, items, extension='', 
                 word_tokenizer=tokenize.wordpunct,
                 sent_tokenizer=None, startpos=0):
        """
        Construct a new plaintext corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = PlaintextCorpusReader(root, '.*', '.txt')
        
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
        @param word_tokenizer: Tokenizer for breaking sentences or
            paragraphs into words.
        @param sent_tokenizer: Tokenizer for breaking paragraphs
            into words.
        """
        if not os.path.isdir(root):
            raise ValueError('Root directory %r not found!' % root)
        self._items = items
        self._root = root
        self._extension = extension
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer

    @property
    def items(self):
        items = self._items
        if isinstance(items, basestring):
            items = find_corpus_items(self._root, items, self._extension)
        self.__dict__['items'] = tuple(items)
        return self.items
            
    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])
    
    def words(self, items=None):
        return concat([self.CorpusView(filename, self._read_word_block)
                       for filename in self._item_filenames(items)])
    
    def sents(self, items=None):
        if self._sent_tokenizer is None:
            raise ValueError('No sentence tokenizer for this corpus')
        return concat([self.CorpusView(filename, self._read_sent_block)
                       for filename in self._item_filenames(items)])

    def paras(self, items=None):
        if self._sent_tokenizer is None:
            raise ValueError('No sentence tokenizer for this corpus')
        return concat([self.CorpusView(filename, self._read_para_block)
                       for filename in self._item_filenames(items)])
        
    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
    def _read_word_block(self, stream):
        words = []
        for i in range(20): # Read 20 lines at a time.
            words.extend(self._word_tokenizer(stream.readline()))
        return words
    
    def _read_sent_block(self, stream):
        sents = []
        for para in read_blankline_block(stream):
            sents.extend([self._word_tokenizer(sent)
                          for sent in self._sent_tokenizer(para)])
        return sents
    
    def _read_para_block(self, stream):
        paras = []
        for para in read_blankline_block(stream):
            paras.append([self._word_tokenizer(sent)
                          for sent in self._sent_tokenizer(para)])
        return paras
            
######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import abc, genesis, inaugural, webtext, udhr
    import textwrap

    def show(hdr, info):
        print hdr, textwrap.fill(info, initial_indent=' '*len(hdr),
                                 subsequent_indent=' '*4)[len(hdr):]
    
    show('Rural:', ' '.join(abc.words('rural')[20:100]))
    show('English genesis:', ' '.join(genesis.words('english-kjv')[:27]))
    show('Finnish genesis:', ' '.join(genesis.words('finnish')[:27]))
    show('Webtext (wine):', ' '.join(webtext.words('wine')[:27]))
    show ('udhr: italian', ' '.join(udhr.words('Italian-Latin1')[:27]))
    
    print 'In inaugural speaches, "men" was used...'
    for speech in inaugural.items:
        year = speech[:4]
        freq = list(inaugural.words(speech)).count('men')
        print '    %d time(s) in %s' % (freq, year)

if __name__ == '__main__':
    demo()
            
        
