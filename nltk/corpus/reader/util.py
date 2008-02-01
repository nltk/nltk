# Natural Language Toolkit: Corpus Reader Utilities
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os, sys, bisect, re
from itertools import islice
from api import CorpusReader
from nltk import tokenize
from nltk.etree import ElementTree
from nltk.internals import deprecated

######################################################################
#{ Corpus View
######################################################################

class AbstractCorpusView(object):
    """
    Abstract base class for corpus views.  See L{StreamBackedCorpusView}
    for more information about corpus views.

    Subclasses must define: L{__len__()}, L{__getitem__()}, and
    L{iterate_from()}.
    """
    def __len__(self):
        """
        Return the number of tokens in the corpus file underlying this
        corpus view.
        """
        raise NotImplementedError('should be implemented by subclass')
    
    def iterate_from(self, start):
        """
        Return an iterator that generates the tokens in the corpus
        file underlying this corpus view, starting at the token number
        C{start}.  If C{start>=len(self)}, then this iterator will
        generate no tokens.
        """
        raise NotImplementedError('should be implemented by subclass')
    
    def __getitem__(self, i):
        """
        Return the C{i}th token in the corpus file underlying this
        corpus view.  Negative indices and spans are both supported.
        """
        raise NotImplementedError('should be implemented by subclass')

    def __iter__(self):
        """Return an iterator that generates the tokens in the corpus
        file underlying this corpus view."""
        return self.iterate_from(0)

    def count(self, value):
        """Return the number of times this list contains C{value}."""
        return sum(1 for elt in self if elt==value)
    
    def index(self, value, start=None, stop=None):
        """Return the index of the first occurance of C{value} in this
        list that is greater than or equal to C{start} and less than
        C{stop}.  Negative start & stop values are treated like negative
        slice bounds -- i.e., they count from the end of the list."""
        start, stop = self._slice_bounds(slice(start, stop))
        for i, elt in enumerate(islice(self, start, stop)):
            if elt == value: return i+start
        raise ValueError('index(x): x not in list')

    def __contains__(self, value):
        """Return true if this list contains C{value}."""
        return bool(self.count(value))
    
    def __add__(self, other):
        """Return a list concatenating self with other."""
        return concat([self, other])
    
    def __radd__(self, other):
        """Return a list concatenating other with self."""
        return concat([other, self])
    
    def __mul__(self, count):
        """Return a list concatenating self with itself C{count} times."""
        return concat([self] * count)
    
    def __rmul__(self, count):
        """Return a list concatenating self with itself C{count} times."""
        return concat([self] * count)

    _MAX_REPR_SIZE = 60
    def __repr__(self):
        """
        @return: A string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(repr(elt))
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return '[%s, ...]' % ', '.join(pieces[:-1])
        else:
            return '[%s]' % ', '.join(pieces)

    def __cmp__(self, other):
        """
        Return a number indicating how C{self} relates to other.

          - If C{other} is not a corpus view or a C{list}, return -1.
          - Otherwise, return C{cmp(list(self), list(other))}.

        Note: corpus views do not compare equal to tuples containing
        equal elements.  Otherwise, transitivity would be violated,
        since tuples do not compare equal to lists.
        """
        if not isinstance(other, (AbstractCorpusView, list)): return -1
        return cmp(list(self), list(other))

    def __hash__(self):
        """
        @raise ValueError: Corpus view objects are unhashable.
        """
        raise ValueError('%s objects are unhashable' %
                         self.__class__.__name__)

    def _slice_bounds(self, slice_obj):
        """
        Given a slice, return the corresponding (start, stop) bounds,
        taking into account None indices, negative indices, etc.  When
        possible, avoid calculating len(self), since it can be slow
        for corpus view objects.
        """
        start, stop = slice_obj.start, slice_obj.stop
        
        # Handle None indices.
        if start is None: start = 0
        if stop is None: stop = len(self)
        
        # Handle negative indices.
        if start < 0: start = max(0, len(self)+start)
        if stop < 0: stop = max(0, len(self)+stop)
    
        # Make sure stop doesn't go past the end of the list.
        if stop > 0:
            try: self[stop-1]
            except IndexError: stop = len(self)
        
        # Make sure start isn't past stop.
        start = min(start, stop)
    
        # That's all folks!
        return start, stop

    
class StreamBackedCorpusView(AbstractCorpusView):
    """
    A 'view' of a corpus file, which acts like a sequence of tokens:
    it can be accessed by index, iterated over, etc.  However, the
    tokens are only constructed as-needed -- the entire corpus is
    never stored in memory at once.

    The constructor to C{StreamBackedCorpusView} takes two arguments:
    a corpus filename; and a block reader.  A X{block reader} is a
    function that reads zero or more tokens from a stream,
    and returns them as a list.  A very simple example of a block
    reader is:

        >>> def simple_block_reader(stream):
        ...     return stream.readline().split()

    This simple block reader reads a single line at a time, and
    returns a single token (consisting of a string) for each
    whitespace-separated substring on the line.

    When deciding how to define the block reader for a given
    corpus, careful consideration should be given to the size of
    blocks handled by the block reader.  Smaller block sizes will
    increase the memory requirements of the corpus view's internal
    data structures (by 2 integers per block).  On the other hand,
    larger block sizes may decrease performance for random access to
    the corpus.  (But note that larger block sizes will I{not}
    decrease performance for iteration.)
    
    Internally, C{CorpusView} maintains a partial mapping from token
    index to file position, with one entry per block.  When a token
    with a given index M{i} is requested, the C{CorpusView} constructs
    it as follows:

      1. First, it searches the toknum/filepos mapping for the token
         index closest to (but less than or equal to) M{i}.
         
      2. Then, starting at the file position corresponding to that
         index, it reads one block at a time using the block reader
         until it reaches the requested token.

    The toknum/filepos mapping is created lazily: it is initially
    empty, but every time a new block is read, the block's
    initial token is added to the mapping.  (Thus, the toknum/filepos
    map has one entry per block.)

    In order to increase efficiency for random access patterns that
    have high degrees of locality, the corpus view may cache one or
    more blocks.

    @note: Each C{CorpusView} object internally maintains an open file
        object for its underlying corpus file.  This file should be
        automatically closed when the C{CorpusView} is garbage collected,
        but if you wish to close it manually, use the L{close()}
        method.  If you access a C{CorpusView}'s items after it has been
        closed, the file object will be automatically re-opened.
        
    @warning: If the contents of the file are modified during the
        lifetime of the C{CorpusView}, then the C{CorpusView}'s behavior
        is undefined.

    @ivar _block_reader: The function used to read 
        a single block from the underlying file stream.
    @ivar _toknum: A list containing the token index of each block
        that has been processed.  In particular, C{_toknum[i]} is the
        token index of the first token in block C{i}.  Together
        with L{_filepos}, this forms a partial mapping between token
        indices and file positions.
    @ivar _filepos: A list containing the file position of each block
        that has been processed.  In particular, C{_toknum[i]} is the
        file position of the first character in block C{i}.  Together
        with L{_toknum}, this forms a partial mapping between token
        indices and file positions.
    @ivar _stream: The stream used to access the underlying corpus file.
    @ivar _len: The total number of tokens in the corpus, if known;
        or C{None}, if the number of tokens is not yet known.
    @ivar _eofpos: The character position of the last character in the
        file.  This is calculated when the corpus view is initialized,
        and is used to decide when the end of file has been reached.
    @ivar _cache: A cache of the most recently read block.  It
       is encoded as a tuple (start_toknum, end_toknum, tokens), where
       start_toknum is the token index of the first token in the block;
       end_toknum is the token index of the first token not in the
       block; and tokens is a list of the tokens in the block.
    """
    def __init__(self, filename, block_reader=None, startpos=0):
        """
        Create a new corpus view, based on the file C{filename}, and
        read with C{block_reader}.  See the class documentation
        for more information.

        @param startpos: The file position at which the view will
            start reading.  This can be used to skip over preface
            sections.
        """
        if block_reader:
            self.read_block = block_reader
        # Initialize our toknum/filepos mapping.
        self._toknum = [0]
        self._filepos = [startpos]
        # We don't know our length (number of tokens) yet.
        self._len = None

        self._filename = filename
        self._stream = None

        # Find the length of the file.  This also checks that the file
        # exists and is readable & seekable.
        try:
            stream = open(filename, 'rb')
            stream.seek(0, 2)
            self._eofpos = stream.tell()
            stream.close()
        except Exception, exc:
            raise ValueError('Unable to open or access %r -- %s' %
                             (filename, exc))
        
        # Maintain a cache of the most recently read block, to
        # increase efficiency of random access.
        self._cache = (-1, -1, None)

    def read_block(self, stream):
        raise NotImplementedError('Abstract Method')

    def close(self):
        """
        Close the file stream associated with this corpus view.  This
        can be useful if you are worried about running out of file
        handles (although the stream should automatically be closed
        upon garbage collection of the corpus view).  If the corpus
        view is accessed after it is closed, it will be automatically
        re-opened.
        """
        if self._stream is not None:
            self._stream.close()
        self._stream = None

    def __len__(self):
        if self._len is None:
            # iterate_from() sets self._len when it reaches the end
            # of the file:
            for tok in self.iterate_from(self._toknum[-1]): pass
        return self._len
    
    def __getitem__(self, i):
        if isinstance(i, slice):
            start, stop = self._slice_bounds(i)
            # Check if it's in the cache.
            offset = self._cache[0]
            if offset <= start and stop < self._cache[1]:
                return self._cache[2][start-offset:stop-offset]
            # Construct & return the result.
            return CorpusViewSlice(self, start, stop)
        else:
            # Handle negative indices
            if i < 0: i += len(self)
            if i < 0: raise IndexError('index out of range')
            # Check if it's in the cache.
            offset = self._cache[0]
            if offset <= i < self._cache[1]:
                return self._cache[2][i-offset]
            # Use iterate_from to extract it.
            try:
                return self.iterate_from(i).next()
            except StopIteration:
                raise IndexError('index out of range')

    # If we wanted to be thread-safe, then this method would need to
    # do some locking.
    def iterate_from(self, start_tok):
        # Decide where in the file we should start.  If `start` is in
        # our mapping, then we can jump straight to the correct block;
        # otherwise, start at the last block we've processed.
        if start_tok < self._toknum[-1]:
            i = bisect.bisect_right(self._toknum, start_tok)-1
            toknum = self._toknum[i]
            filepos = self._filepos[i]
        else:
            toknum = self._toknum[-1]
            filepos = self._filepos[-1]

        # Open the stream, if it's not open already.
        if self._stream is None:
            self._stream = open(self._filename, 'rb')
            
        # Find the character position of the end of the file.
        if self._eofpos is None:
            self._stream.seek(0, 2)
            self._eofpos = self._stream.tell()
        
        # Each iteration through this loop, we read a single block
        # from the stream.
        while True:
            # Read the next block.
            self._stream.seek(filepos)
            tokens = self.read_block(self._stream)
            assert isinstance(tokens, (tuple, list)), \
                   'block reader should return list or tuple.'
            num_toks = len(tokens)
            new_filepos = self._stream.tell()

            # Update our cache.
            self._cache = (toknum, toknum+num_toks, list(tokens))
            
            # Update our mapping.
            assert toknum <= self._toknum[-1]
            if toknum == self._toknum[-1] and num_toks > 0:
                assert new_filepos > self._filepos[-1] # monotonic!
                self._filepos.append(new_filepos)
                self._toknum.append(toknum+num_toks)
                    
            # Generate the tokens in this block (but skip any tokens
            # before start_tok).  Note that between yields, our state
            # may be modified.
            for tok in tokens[max(0, start_tok-toknum):]:
                yield tok
            # If we're at the end of the file, then we're done; set
            # our length and terminate the generator.
            if new_filepos == self._eofpos:
                self._len = toknum + num_toks
                return
            # Update our indices
            toknum += num_toks
            filepos = new_filepos

class CorpusViewSlice(AbstractCorpusView):
    MIN_SIZE = 100
    
    def __new__(cls, source, start, stop):
        "We assume that negative bounds etc have been handled already."
        # If the slice is small enough, just use a tuple.
        if stop-start < cls.MIN_SIZE:
            return list(islice(source.iterate_from(start), stop-start))
        else:
            return object.__new__(cls, source, start, stop)
        
    def __init__(self, source, start, stop):
        self._source = source
        self._start = start
        self._stop = stop

    def __len__(self):
        return self._stop - self._start

    def iterate_from(self, start):
        return islice(self._source.iterate_from(start+self._start), len(self))

    def __getitem__(self, i):
        if isinstance(i, slice):
            start, stop = self._slice_bounds(i)
            return CorpusViewSlice(self, start, stop)
        else:
            # Handle out-of-bound indices.
            if i < 0: i += len(self)
            if (i < 0) or (i >= len(self)):
                raise IndexError('index out of range')
            # Get the value.
            return self._source[self._start + i]
    
class ConcatenatedCorpusView(AbstractCorpusView):
    """
    A 'view' of a corpus file that joins together one or more
    L{StreamBackedCorpusViews<StreamBackedCorpusView>}.  At most
    one file handle is left open at any time.
    """
    def __init__(self, corpus_views):
        self._pieces = corpus_views
        """A list of the corpus subviews that make up this
        concatenation."""
        
        self._offsets = [0]
        """A list of offsets, indicating the index at which each
        subview begins.  In particular::
            offsets[i] = sum([len(p) for p in pieces[:i]])"""
        
        self._open_piece = None
        """The most recently accessed corpus subview (or C{None}).
        Before a new subview is accessed, this subview will be closed."""

    def __len__(self):
        if len(self._offsets) <= len(self._pieces):
            # Iterate to the end of the corpus.
            for tok in self.iterate_from(self._offsets[-1]): pass
            
        return self._offsets[-1]

    def __getitem__(self, i):
        if isinstance(i, slice):
            start, stop = self._slice_bounds(i)
            # Check if it's within a single view -- then we might be
            # able to use that view's cache.
            piecenum = bisect.bisect_right(self._offsets, start)-1
            if ((piecenum+1) < len(self._offsets) and
                stop < self._offsets[piecenum+1]):
                offset = self._offsets[piecenum]
                return self._pieces[piecenum][start-offset:stop-offset]
            
            # Otherwise, just use a slice over self:
            else:
                return CorpusViewSlice(self, start, stop)
        else:
            # Handle negative indices
            if i < 0: i += len(self)
            if i < 0: raise IndexError('index out of range')
            # Use iterate_from to extract it.
            try:
                return self.iterate_from(i).next()
            except StopIteration:
                raise IndexError('index out of range')

    def __iter__(self):
        return self.iterate_from(0)

    def close(self):
        for piece in self._pieces:
            piece.close()

    def iterate_from(self, start_tok):
        piecenum = bisect.bisect_right(self._offsets, start_tok)-1

        while piecenum < len(self._pieces):
            offset = self._offsets[piecenum]
            piece = self._pieces[piecenum]

            # If we've got another piece open, close it first.
            if self._open_piece is not piece:
                if self._open_piece is not None:
                    self._open_piece.close()
                self._open_piece = piece

            # Get everything we can from this piece.
            for tok in piece.iterate_from(max(0, start_tok-offset)):
                yield tok

            # Update the offset table.
            if piecenum+1 == len(self._offsets):
                self._offsets.append(self._offsets[-1] + len(piece))

            # Move on to the next piece.
            piecenum += 1
        
def concat(docs):
    """
    Concatenate together the contents of multiple documents from a
    single corpus, using an appropriate concatenation function.  This
    utility function is used by corpus readers when the user requests
    more than one document at a time.
    """
    if len(docs) == 1:
        return docs[0]
    if len(docs) == 0:
        raise ValueError('concat() expects at least one object!')
    
    types = set([d.__class__ for d in docs])

    # If they're all strings, use string concatenation.
    if types.issubset([str, unicode, basestring]):
        return reduce((lambda a,b:a+b), docs, '')

    # If they're all corpus views, then use ConcatenatedCorpusView.
    for typ in types:
        if not issubclass(typ, AbstractCorpusView):
            break
    else:
        return ConcatenatedCorpusView(docs)

    # Otherwise, see what we can do:
    if len(types) == 1:
        typ = list(types)[0]

        if issubclass(typ, list):
            return reduce((lambda a,b:a+b), docs, [])
    
        if issubclass(typ, tuple):
            return reduce((lambda a,b:a+b), docs, ())

        if ElementTree.iselement(typ):
            xmltree = ElementTree.Element('documents')
            for doc in docs: xmltree.append(doc)
            return xmltree

    # No method found!
    raise ValueError("Don't know how to concatenate types: %r" % types)

######################################################################
#{ Block Readers
######################################################################

def read_whitespace_block(stream):
    toks = []
    for i in range(20): # Read 20 lines at a time.
        toks.extend(stream.readline().split())
    return toks

def read_wordpunct_block(stream):
    toks = []
    for i in range(20): # Read 20 lines at a time.
        toks.extend(wordpuct_tokenize(stream.readline()))
    return toks

def read_line_block(stream):
    toks = []
    for i in range(20):
        line = stream.readline()
        if not line: return toks
        toks.append(line.replace('\n', ''))
    return toks

def read_blankline_block(stream):
    s = ''
    while True:
        line = stream.readline()
        # End of file:
        if not line:
            if s: return [s]
            else: return []
        # Blank line:
        elif line and not line.strip():
            if s: return [s]
        # Other line:
        else:
            s += line

def read_regexp_block(stream, start_re, end_re=None):
    """
    Read a sequence of tokens from a stream, where tokens begin with
    lines that match C{start_re}.  If C{end_re} is specified, then
    tokens end with lines that match C{end_re}; otherwise, tokens end
    whenever the next line matching C{start_re} or EOF is found.
    """
    # Scan until we find a line matching the start regexp.
    while True:
        line = stream.readline()
        if not line: return [] # end of file.
        if re.match(start_re, line): break

    # Scan until we find another line matching the regexp, or EOF.
    lines = [line]
    while True:
        oldpos = stream.tell()
        line = stream.readline()
        # End of file:
        if not line:
            return [''.join(lines)]
        # End of token:
        if end_re is not None and re.match(end_re, line):
            return [''.join(lines)]
        # Start of new token: backup to just before it starts, and
        # return the token we've already collected.
        if end_re is None and re.match(start_re, line):
            stream.seek(oldpos)
            return [''.join(lines)]
        # Anything else is part of the token.
        lines.append(line)

def read_sexpr_block(stream, block_size=16384, comment_char=None):
    """
    Read a sequence of s-expressions from the stream, and leave the
    stream's file position at the end the last complete s-expression
    read.  This function will always return at least one s-expression,
    unless there are no more s-expressions in the file.

    If the file ends in in the middle of an s-expression, then that
    incomplete s-expression is returned when the end of the file is
    reached.
    
    @param block_size: The default block size for reading.  If an
        s-expression is longer than one block, then more than one
        block will be read.
    @param comment_char: A character that marks comments.  Any lines
        that begin with this character will be stripped out.
        (If spaces or tabs preceed the comment character, then the
        line will not be stripped.)
    """
    start = stream.tell()
    block = stream.read(block_size)
    if comment_char:
        COMMENT = re.compile('(?m)^%s.*$' % re.escape(comment_char))
    while True:
        try:
            # If we're stripping comments, then make sure our block ends
            # on a line boundary; and then replace any comments with
            # space characters.  (We can't just strip them out -- that
            # would make our offset wrong.)
            if comment_char:
                block += stream.readline()
                block = re.sub(COMMENT, _sub_space, block)
            # Read the block.
            tokens, offset = _parse_sexpr_block(block)
            # Skip whitespace
            offset = re.compile(r'\s*').search(block, offset).end()
            # Move to the end position.
            stream.seek(start+offset)
            # Return the list of tokens we processed
            return tokens
        except ValueError, e:
            if e.args[0] == 'Block too small':
                next_block = stream.read(block_size)
                if next_block:
                    block += next_block
                    continue
                else:
                    # The file ended mid-sexpr -- return what we got.
                    return [block.strip()]
            else: raise

def _sub_space(m):
    """Helper function: given a regexp match, return a string of
    spaces that's the same length as the matched string."""
    return ' '*(m.end()-m.start())

def _parse_sexpr_block(block):
    tokens = []
    start = end = 0

    while end < len(block):
        m = re.compile(r'\S').search(block, end)
        if not m:
            return tokens, end

        start = m.start()

        # Case 1: sexpr is not parenthesized.
        if m.group() != '(':
            m2 = re.compile(r'[\s(]').search(block, start)
            if m2:
                end = m2.start()
            else:
                if tokens: return tokens, end
                raise ValueError('Block too small')

        # Case 2: parenthesized sexpr.
        else:
            nesting = 0
            for m in re.compile(r'[()]').finditer(block, start):
                if m.group()=='(': nesting += 1
                else: nesting -= 1
                if nesting == 0:
                    end = m.end()
                    break
            else:
                if tokens: return tokens, end
                raise ValueError('Block too small')

        tokens.append(block[start:end])

    return tokens, end

######################################################################
#{ Treebank readers
######################################################################

#[xx] is it worth it to factor this out?
class SyntaxCorpusReader(CorpusReader):
    """
    An abstract base class for reading corpora consisting of
    syntactically parsed text.  Subclasses should define:

      - L{__init__}, which specifies the location of the corpus
        and a method for detecting the sentence blocks in corpus files.
      - L{_read_block}, which reads a block from the input stream.
      - L{_word}, which takes a block and returns a list of list of words.
      - L{_tag}, which takes a block and returns a list of list of tagged
        words.
      - L{_parse}, which takes a block and returns a list of parsed
        sentences.
    """

    def raw(self, files=None):
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

    def parsed_sents(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_parsed_sent_block)
                       for filename in self.abspaths(files)])

    def tagged_sents(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_tagged_sent_block)
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_sent_block)
                       for filename in self.abspaths(files)])

    def tagged_words(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_tagged_word_block)
                       for filename in self.abspaths(files)])

    def words(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_word_block)
                       for filename in self.abspaths(files)])

    #------------------------------------------------------------
    #{ Block Readers
    
    def _read_word_block(self, stream):
        return sum(self._read_sent_block(stream), [])

    def _read_tagged_word_block(self, stream):
        return sum(self._read_tagged_sent_block(stream), [])

    def _read_sent_block(self, stream):
        sents = [self._word(t) for t in self._read_block(stream)]
        return [sent for sent in sents if sent]
    
    def _read_tagged_sent_block(self, stream):
        tagged_sents = [self._tag(t) for t in self._read_block(stream)]
        return [tagged_sent for tagged_sent in tagged_sents if tagged_sent]

    def _read_parsed_sent_block(self, stream):
        trees = [self._parse(t) for t in self._read_block(stream)]
        return [tree for tree in trees if tree is not None]

    #} End of Block Readers
    #------------------------------------------------------------

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .sents() or .tagged_sents() or "
                ".parsed_sents() instead.")
    def read(self, items=None, format='parsed'):
        if format == 'parsed': return self.parsed_sents(items)
        if format == 'raw': return self.raw(items)
        if format == 'tokenized': return self.sents(items)
        if format == 'tagged': return self.tagged_sents(items)
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
    #}


######################################################################
#{ Finding Corpus Items
######################################################################

def find_corpus_files(root, regexp):
    items = []
    
    regexp += '$'
    for dirname, subdirs, filenames in os.walk(root):
        prefix = ''.join('%s/' % p for p in _path_from(root, dirname))
        items += [prefix+filename for filename in filenames
                  if re.match(regexp, prefix+filename)]
        # Don't visit svn directories:
        if '.svn' in subdirs: subdirs.remove('.svn')
        
    return tuple(sorted(items))
    
def _path_from(parent, child):
    if os.path.split(parent)[1] == '':
        parent = os.path.split(parent)[0]
    path = []
    while parent != child:
        child, dirname = os.path.split(child)
        path.insert(0, dirname)
        assert os.path.split(child)[0] != child
    return path

######################################################################
#{ Paragraph structure in Treebank files
######################################################################

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
            
