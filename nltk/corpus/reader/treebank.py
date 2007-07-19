# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.plaintext import PlaintextCorpusReader
from nltk.tree import Tree, bracket_parse
from nltk import tokenize, chunk, tree
from nltk.tag import tag2tuple
import os

"""
Penn Treebank corpus sample: tagged, NP-chunked, and parsed data from
Wall Street Journal for 3700 sentences.

This is a ~10% fragment of the Wall Street Journal section of the Penn
Treebank, (C) LDC 1995.  It is distributed with the Natural Language Toolkit
under the terms of the Creative Commons Attribution-NonCommercial-ShareAlike License
[http://creativecommons.org/licenses/by-nc-sa/2.5/].

Raw:

    Pierre Vinken, 61 years old, will join the board as a nonexecutive
    director Nov. 29.

Tagged:

    Pierre/NNP Vinken/NNP ,/, 61/CD years/NNS old/JJ ,/, will/MD join/VB 
    the/DT board/NN as/IN a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ./.

NP-Chunked:

    [ Pierre/NNP Vinken/NNP ]
    ,/, 
    [ 61/CD years/NNS ]
    old/JJ ,/, will/MD join/VB 
    [ the/DT board/NN ]
    as/IN 
    [ a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ]
    ./.

Parsed:

    ( (S 
      (NP-SBJ 
        (NP (NNP Pierre) (NNP Vinken) )
        (, ,) 
        (ADJP 
          (NP (CD 61) (NNS years) )
          (JJ old) )
        (, ,) )
      (VP (MD will) 
        (VP (VB join) 
          (NP (DT the) (NN board) )
          (PP-CLR (IN as) 
            (NP (DT a) (JJ nonexecutive) (NN director) ))
          (NP-TMP (NNP Nov.) (CD 29) )))
      (. .) ))
"""

class TreebankCorpusReader(CorpusReader):
    """
    Corpus reader for the treebank.  Combines thee underlying formats:
    parsed, tagged+chunkied, and plaintext.  Each of these formats is
    stored in a different subdirectory (combined/, tagged/, and raw/,
    respectively).

    If your corpus doesn't have this format, but just contains files
    with treebank-style parses, you should use
    L{TreebankTreeCorpusReader} instead.
    """
    def __init__(self, root):
        self._root = root
        self._mrg_reader = TreebankTreeCorpusReader(
            os.path.join(root, 'combined'), '.*', '.mrg')
        self._pos_reader = TreebankChunkCorpusReader(
            os.path.join(root, 'tagged'), '.*', '.pos')

        # Make sure we have a consistent set of items:
        if set(self._mrg_reader.items) != set(self._pos_reader.items):
            raise ValueError('Items in "combined" and "tagged" '
                             'subdirectories do not match.')
        for item in self._mrg_reader.items:
            if not os.path.exists(os.path.join(root, 'raw', item)):
                raise ValueError('File %r missing from "raw" subdirectory'
                                 % item)
        self.items = self._mrg_reader.items

    # Delegate to one of our two sub-readers:
    def parsed_sents(self, items=None):
        return self._mrg_reader.parsed_sents(items)
    def words(self, items=None):
        return self._pos_reader.words(items)
    def sents(self, items=None):
        return self._pos_reader.sents(items)
    def paras(self, items=None):
        return self._pos_reader.paras(items)
    def tagged_words(self, items=None):
        return self._pos_reader.tagged_words(items)
    def tagged_sents(self, items=None):
        return self._pos_reader.tagged_sents(items)
    def tagged_paras(self, items=None):
        return self._pos_reader.tagged_paras(items)
    def chunked_words(self, items=None):
        return self._pos_reader.chunked_words(items)
    def chunked_sents(self, items=None):
        return self._pos_reader.chunked_sents(items)
    def chunked_paras(self, items=None):
        return self._pos_reader.chunked_paras(items)

    # Read in the text file, and strip the .START prefix.
    def text(self, items=None):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        filenames = [os.path.join(self._root, 'raw', item) for item in items]
        return concat([re.sub(r'\A\s*\.START\s*', '', open(filename).read())
                       for filename in filenames])
        
    def _check_reader(self, reader, name):
        if reader is None:
            raise ValueError('No %s files were found in your copy '
                             'of the treebank' % name)

class TreebankTreeCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of treebank-style trees.  For
    reading the Treebank corpus itself, you may wish to use
    L{TreebankCorpusReader}, which combines this reader with readers
    for the other formats available in the treebank.
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

    def parsed_sents(self, items=None):
        return concat([StreamBackedCorpusView(filename, self._read_block)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
        
    def _read_block(self, stream):
        return [self._treebank_bracket_parse(t) for t in 
                read_sexpr_block(stream)]
    
    def _treebank_bracket_parse(self, t):
        try:
            return bracket_parse(t)
        except IndexError:
            # in case it's the real treebank format, 
            # strip first and last brackets before parsing
            return bracket_parse(t.strip()[1:-1])
    

class TreebankChunkCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of treebank-style chunked&tagged
    text (i.e., '*.pos' files).  For reading the Treebank corpus
    itself, you may wish to use L{TreebankCorpusReader}, which
    combines this reader with readers for the other formats available
    in the treebank.
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

    def words(self, items=None):
        return concat([TreebankChunkCorpusView(filename, False, False,
                                               False, False)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        return concat([TreebankChunkCorpusView(filename, False, True,
                                               False, False)
                       for filename in self._item_filenames(items)])

    def paras(self, items=None):
        return concat([TreebankChunkCorpusView(filename, False, True,
                                               True, False)
                       for filename in self._item_filenames(items)])

    def tagged_words(self, items=None):
        return concat([TreebankChunkCorpusView(filename, True, False,
                                               False, False)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        return concat([TreebankChunkCorpusView(filename, True, True,
                                               False, False)
                       for filename in self._item_filenames(items)])

    def tagged_paras(self, items=None):
        return concat([TreebankChunkCorpusView(filename, True, True,
                                               True, False)
                       for filename in self._item_filenames(items)])

    def chunked_words(self, items=None):
        return concat([TreebankChunkCorpusView(filename, True, False,
                                               False, True)
                       for filename in self._item_filenames(items)])

    def chunked_sents(self, items=None):
        return concat([TreebankChunkCorpusView(filename, True, True,
                                               False, True)
                       for filename in self._item_filenames(items)])

    def chunked_paras(self, items=None):
        return concat([TreebankChunkCorpusView(filename, True, True,
                                               True, True)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
        
    def _read_block(self, stream):
        return [chunk.tagstr2tree(t) for t in
                read_blankline_block(stream)]

class TreebankChunkCorpusView(StreamBackedCorpusView):
    def __init__(self, filename, tagged, group_by_sent,
                 group_by_para, chunked):
        StreamBackedCorpusView.__init__(self, filename)
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._chunked = chunked

    def read_block(self, stream):
        # Read the next paragraph.
        block = ''
        while True:
            line = stream.readline()
            # End of paragraph:
            if re.match('======+\s*$', line):
                if block.strip(): break
            # End of file:
            elif line == '':
                if block.strip(): break
                else: return []
            # Content line:
            else:
                block += line

        # Divide the block into sentences (look for words tagged with
        # the end-of-word tag '.', such as './.' or '?/.')
        sents = tokenize.regexp(block, r'(?<=/\.)\s', gaps=True)
        
        # Parse each sentence using tagstr2tree.
        para = [chunk.tagstr2tree(sent) for sent in sents]

        # If requested, throw away the tags.
        if not self._tagged:
            para = [self._untag(sent) for sent in para]

        # If requested, throw away the chunks.
        if not self._chunked:
            para = [sent.leaves() for sent in para]

        # If requested, concatenate the sentences together.
        if not self._group_by_sent:
            para = reduce((lambda a,b:a+b), para, [])

        # Return the paragraph as a single token, or as a list of
        # pieces, depending on whether we're grouping by para.
        if self._group_by_para:
            return [para]
        else:
            return para

    def _untag(self, tree):
        for i, child in enumerate(tree):
            if isinstance(child, Tree):
                self._untag(child)
            elif isinstance(child, tuple):
                tree[i] = child[0]
            else:
                raise ValueError('expected child to be Tree or tuple')
        return tree
    
######################################################################
#{ Demo
######################################################################
def demo():

#     tb = TreebankChunkCorpusReader('/Users/edloper/data/projects/nltk/corpora/treebank/tagged', '.*', '.pos')
#     print tb.words('wsj_0120')
#     for para in tb.chunked_paras('wsj_0120')[:3]:
#         print '='*50
#         for sent in para:
#             print ' '.join(str(w) for w in sent)
    


    from nltk.corpus import treebank

    print "Parsed:"
    for tree in treebank.parsed_sents('wsj_0003')[:3]:
        print tree
    print

    print "Chunked:"
    for tree in treebank.chunked_sents('wsj_0003')[:3]:
        print tree
    print

    print "Tagged:"
    for sent in treebank.tagged_sents('wsj_0003')[:3]:
        print sent
    print

    print "Words:"
    print ' '.join(treebank.words('wsj_0120')[:30])

    # Note that this spans across multiple documents:
    print 'Height of trees:'
    for tree in treebank.parsed_sents()[:25]:
        print tree.height(),

if __name__ == '__main__':
    demo()


