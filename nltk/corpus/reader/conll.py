# Natural Language Toolkit: CONLL Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read CoNLL-style chunk files.
"""       

from util import *
from api import *
from nltk import chunk, tree, bracket_parse
import os, codecs
from nltk.internals import deprecated
from nltk import Tree, LazyMap, LazyConcatenation

class ConllCorpusReader(CorpusReader):
    """
    A corpus reader for CoNLL-style files.  These files consist of a
    series of sentences, seperated by blank lines.  Each sentence is
    encoded using a table (or I{grid}) of values, where each line
    corresponds to a single word, and each column corresponds to an
    annotation type.  The set of columns used by CoNLL-style files can
    vary from corpus to corpus; the C{ConllCorpusReader} constructor
    therefore takes an argument, C{columntypes}, which is used to
    specify the columns that are used by a given corpus.

    @todo: Add support for reading from corpora where different
        parallel files contain different columns.
    @todo: Possibly add caching of the grid corpus view?  This would
        allow the same grid view to be used by different data access
        methods (eg words() and parsed_sents() could both share the
        same grid corpus view object).
    @todo: Better support for -DOCSTART-.  Currently, we just ignore
        it, but it could be used to define methods that retrieve a
        document at a time (eg parsed_documents()).
    """
    
    #/////////////////////////////////////////////////////////////////
    # Column Types
    #/////////////////////////////////////////////////////////////////
    
    WORDS = 'words'   #: column type for words
    POS = 'pos'       #: column type for part-of-speech tags
    TREE = 'tree'     #: column type for parse trees
    CHUNK = 'chunk'   #: column type for chunk structures
    NE = 'ne'         #: column type for named entities
    SRL = 'srl'       #: column type for semantic role labels
    IGNORE = 'ignore' #: column type for column that should be ignored

    #: A list of all column types supported by the conll corpus reader.
    COLUMN_TYPES = (WORDS, POS, TREE, CHUNK, NE, SRL, IGNORE)
    
    #/////////////////////////////////////////////////////////////////
    # Constructor
    #/////////////////////////////////////////////////////////////////
    
    def __init__(self, root, files, columntypes,
                 chunk_types=None, top_node='S', pos_in_tree=False,
                 encoding=None):
        for columntype in columntypes:
            if columntype not in self.COLUMN_TYPES:
                raise ValueError('Bad colum type %r' % columntyp)
        if chunk_types is not None: chunk_types = tuple(chunk_types)
        self._chunk_types = chunk_types
        self._colmap = dict((c,i) for (i,c) in enumerate(columntypes))
        self._pos_in_tree = pos_in_tree
        self._top_node = 'S' # for chunks
        CorpusReader.__init__(self, root, files, encoding)

    #/////////////////////////////////////////////////////////////////
    # Data Access Methods
    #/////////////////////////////////////////////////////////////////

    def raw(self, files=None):
        return concat([codecs.open(path, 'rb', enc).read()
                       for (path,enc) in self.abspaths(files, True)])

    def words(self, files=None):
        self._require(self.WORDS)
        return LazyConcatenation(LazyMap(self._get_words, self._grids(files)))

    def sents(self, files=None):
        self._require(self.WORDS)
        return LazyMap(self._get_words, self._grids(files))

    def tagged_words(self, files=None):
        self._require(self.WORDS, self.POS)
        return LazyConcatenation(LazyMap(self._get_tagged_words,
                                         self._grids(files)))

    def tagged_sents(self, files=None):
        self._require(self.WORDS, self.POS)
        return LazyMap(self._get_tagged_words, self._grids(files))

    def chunked_words(self, files=None, chunk_types=None):
        self._require(self.WORDS, self.POS, self.CHUNK)
        if chunk_types is None: chunk_types = self._chunk_types
        def get_chunked_words(grid): # capture chunk_types as local var
            return self._get_chunked_words(grid, chunk_types)
        return LazyConcatenation(LazyMap(get_chunked_words,
                                         self._grids(files)))

    def chunked_sents(self, files=None, chunk_types=None):
        self._require(self.WORDS, self.POS, self.CHUNK)
        if chunk_types is None: chunk_types = self._chunk_types
        def get_chunked_words(grid): # capture chunk_types as local var
            return self._get_chunked_words(grid, chunk_types)
        return LazyMap(get_chunked_words, self._grids(files))
    
    def parsed_sents(self, files=None, pos_in_tree=False):
        self._require(self.WORDS, self.POS, self.TREE)
        return LazyMap(self._get_parsed_sent, self._grids(files))

    def srl_spans(self, files=None, pos_in_tree=False):
        self._require(self.SRL)
        if pos_in_tree is False: pos_in_tree = self._pos_in_tree
        return LazyMap(self._get_srl_spans, self._grids(files))

    def iob_words(self, files=None):
        """
        @return: a list of word/tag/IOB tuples 
        @rtype: C{list} of C{tuple}
        @param files: the list of files that make up this corpus 
        @type files: C{None} or C{str} or C{list}
        @param chunk_types: list of chunks to recognize when returning
                            tokens
        @type chunk_types: C{list} of C{str}
        """
        self._require(self.WORDS, self.POS, self.CHUNK)
        if chunk_types is None: chunk_types = self._chunk_types
        return LazyConcatenation(LazyMap(self._get_iob_words,
                                         self._grids(files)))

    def iob_sents(self, files=None):
        """
        @return: a list of lists of word/tag/IOB tuples 
        @rtype: C{list} of C{list}
        @param files: the list of files that make up this corpus 
        @type files: C{None} or C{str} or C{list}
        @param chunk_types: list of chunks to recognize when returning
                            tokens
        @type chunk_types: C{list} of C{str}
        """
        self._require(self.WORDS, self.POS, self.CHUNK)
        if chunk_types is None: chunk_types = self._chunk_types
        return LazyMap(self._get_iob_words, self._grids(files))
    
    #/////////////////////////////////////////////////////////////////
    # Grid Reading
    #/////////////////////////////////////////////////////////////////
    
    def _grids(self, files=None):
        # n.b.: we could cache the object returned here (keyed on
        # files), which would let us reuse the same corpus view for
        # different things (eg srl and parse trees).
        return concat([StreamBackedCorpusView(filename, self._read_grid_block,
                                              encoding=enc)
                       for (filename, enc) in self.abspaths(files, True)])

    def _read_grid_block(self, stream):
        # Read the grid describing a single sentence.
        block = read_blankline_block(stream)[0].strip()
        grid = [line.split() for line in block.split('\n')]
        
        # If there's a docstart row, then discard. ([xx] eventually it
        # would be good to actually use it)
        if grid[0][self._colmap.get('words', 0)] == '-DOCSTART-':
            del grid[0]
        
        # Check that the grid is consistent.
        for row in grid:
            if len(row) != len(grid[0]):
                raise ValueError('Inconsistent number of columns')
        return [grid]

    #/////////////////////////////////////////////////////////////////
    # Transforms
    #/////////////////////////////////////////////////////////////////
    # given a grid, transform it into some representation (e.g.,
    # a list of words or a parse tree).

    def _get_words(self, grid):
        return self._get_column(grid, self._colmap['words'])

    def _get_tagged_words(self, grid):
        return zip(self._get_column(grid, self._colmap['words']),
                   self._get_column(grid, self._colmap['pos']))

    def _get_iob_words(self, grid):
        return zip(self._get_column(grid, self._colmap['words']),
                   self._get_column(grid, self._colmap['pos']),
                   self._get_column(grid, self._colmap['chunk']))

    def _get_chunked_words(self, grid, chunk_types):
        # n.b.: this method is very similar to conllstr2tree.
        words = self._get_column(grid, self._colmap['words'])
        pos_tags = self._get_column(grid, self._colmap['pos'])
        chunk_tags = self._get_column(grid, self._colmap['chunk'])

        stack = [Tree(self._top_node, [])]
        
        for (word, pos_tag, chunk_tag) in zip(words, pos_tags, chunk_tags):
            if chunk_tag == 'O':
                state, chunk_type = 'O', ''
            else:
                (state, chunk_type) = chunk_tag.split('-')
            # If it's a chunk we don't care about, treat it as O.
            if chunk_types is not None and chunk_type not in chunk_types:
                state = 'O'
            # Treat a mismatching I like a B.
            if state == 'I' and chunk_type != stack[-1].node:
                state = 'B'
            # For B or I: close any open chunks
            if state in 'BO' and len(stack) == 2:
                stack.pop()
            # For B: start a new chunk.
            if state == 'B':
                new_chunk = Tree(chunk_type, [])
                stack[-1].append(new_chunk)
                stack.append(new_chunk)
            # Add the word token.
            stack[-1].append((word, pos_tag))

        return stack[0]

    def _get_parsed_sent(self, grid):
        words = self._get_column(grid, self._colmap['words'])
        pos_tags = self._get_column(grid, self._colmap['pos'])
        parse_tags = self._get_column(grid, self._colmap['tree'])
        
        treestr = ''
        for (word, pos_tag, parse_tag) in zip(words, pos_tags, parse_tags):
            (left, right) = parse_tag.split('*')
            right = right.count(')')*')' # only keep ')'.
            treestr += '%s (%s %s) %s' % (left, pos_tag, word, right)
        try:
            tree = bracket_parse(treestr)
        except (ValueError, IndexError):
            tree = bracket_parse('(%s %s)' % (self._top_node, treestr))
        
        if not self._pos_in_tree:
            for subtree in tree.subtrees():
                for i, child in enumerate(subtree):
                    if (isinstance(child, nltk.Tree) and len(child)==1 and 
                        isinstance(child[0], basestring)):
                        subtree[i] = (child[0], child.node)

        return tree

    def _get_srl_spans(self, grid):
        """
        list of list of (tag, start, end) tuples.
        """
        predicates = self._get_column(grid, self._colmap['srl'])
        num_preds = len([p for p in predicates if p != '-'])

        spanlists = []
        for i in range(num_preds):
            col = self._get_column(grid, self._colmap['srl']+1+i)
            spanlist = []
            stack = []
            for wordnum, srl_tag in enumerate(col):
                (left, right) = srl_tag.split('*')
                for tag in left.split('('):
                    if tag:
                        stack.append((tag, wordnum))
                for i in range(right.count(')')):
                    (tag, start) = stack.pop()
                    spanlist.append( (tag, start, wordnum+1) )
            spanlists.append(spanlist)

        return spanlists

    #/////////////////////////////////////////////////////////////////
    # Helper Methods
    #/////////////////////////////////////////////////////////////////

    def _require(self, *columntypes):
        for columntype in columntypes:
            if columntype not in self._colmap:
                raise ValueError('This corpus does not contain a %s '
                                 'column.' % columntype)

    @staticmethod
    def _get_column(grid, column_index):
        return [grid[i][column_index] for i in range(len(grid))]


    #/////////////////////////////////////////////////////////////////
    #{ Deprecated since 0.8
    #/////////////////////////////////////////////////////////////////
    @deprecated("Use .raw() or .words() or .tagged_words() or "
                ".chunked_sents() instead.")
    def read(self, items, format='chunked', chunk_types=None):
        if format == 'chunked': return self.chunked_sents(items, chunk_types)
        if format == 'raw': return self.raw(items)
        if format == 'tokenized': return self.words(items)
        if format == 'tagged': return self.tagged_words(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .chunked_sents() instead.")
    def chunked(self, items, chunk_types=None):
        return self.chunked_sents(items, chunk_types)
    @deprecated("Use .words() instead.")
    def tokenized(self, items):
        return self.words(items)
    @deprecated("Use .tagged_words() instead.")
    def tagged(self, items):
        return self.tagged_words(items)
    #}
    

class ConllChunkCorpusReader(ConllCorpusReader):
    """
    A ConllCorpusReader whose data file contains three columns: words,
    pos, and chunk.
    """
    def __init__(self, root, files, chunk_types, encoding=None):
        ConllCorpusReader.__init__(
            self, root, files, ('words', 'pos', 'chunk'),
            chunk_types=chunk_types, encoding=encoding)

