# Natural Language Toolkit: Corpus Reader Utilities
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os, sys, bisect, re
from itertools import islice
from nltk import tokenize
from nltk.etree import ElementTree

######################################################################
#{ Corpus Path
######################################################################

_CORPUS_PATH = []
"""A list of directories that should be searched for corpora."""

# Initialize the corpus path.
if 'NLTK_CORPORA' in os.environ:
    _CORPUS_PATH += os.environ['NLTK_CORPORA'].split(':')
if sys.platform.startswith('win'):
    if os.path.isdir('C:\\corpora'):
        _CORPUS_PATH.append('C:\\corpora')
    if os.path.isdir(os.path.join(sys.prefix, 'nltk', 'corpora')):
        _CORPUS_PATH.append(os.path.join(sys.prefix, 'nltk', 'corpora'))
    if os.path.isdir(os.path.join(sys.prefix, 'lib', 'nltk', 'corpora')):
        _CORPUS_PATH.append(os.path.join(sys.prefix, 'lib', 'nltk', 'corpora'))
    if os.path.isdir(os.path.join(sys.prefix, 'nltk')):
        _CORPUS_PATH.append(os.path.join(sys.prefix, 'nltk'))
    if os.path.isdir(os.path.join(sys.prefix, 'lib', 'nltk')):
        _CORPUS_PATH.append(os.path.join(sys.prefix, 'lib', 'nltk'))
if os.path.isdir('/usr/share/nltk/corpora'):
   _CORPUS_PATH.append('/usr/share/nltk/corpora')
if os.path.isdir('/usr/local/share/nltk/corpora'):
   _CORPUS_PATH.append('/usr/local/share/nltk/corpora')

if os.path.isdir('/usr/share/nltk'):
   _CORPUS_PATH.append('/usr/share/nltk')
if os.path.isdir('/usr/local/share/nltk'):
   _CORPUS_PATH.append('/usr/local/share/nltk')

if os.path.isdir('/usr/share/nltk_lite/corpora'):
   _CORPUS_PATH.append('/usr/share/nltk_lite/corpora')
if os.path.isdir('/usr/local/share/nltk_lite/corpora'):
   _CORPUS_PATH.append('/usr/local/share/nltk_lite/corpora')


def set_corpus_path(path):
    """
    Set the path to the directory where NLTK looks for corpora.
    
    @type path: C{list} of C{string}
    @param path: The paths of directories where NLTK should look for corpora.
    """
    global _CORPUS_PATH
    _CORPUS_PATH = path

def add_corpus_path(path):
    """
    Register a new directory where NLTK corpora might be found.
    @type path: C{string}
    """
    global _CORPUS_PATH
    _CORPUS_PATH.append(path)

def get_corpus_path():
    """
    @return: The paths of directories of the directory where NLTK
    looks for corpora.
    @rtype: C{list} of C{string}
    """
    return list(_CORPUS_PATH)

######################################################################
#{ Corpus View
######################################################################

class StreamBackedCorpusView:
    """
    A 'view' of a corpus file, which acts like a sequence of tokens:
    it can be accessed by index, iterated over, etc.  However, the
    tokens are only constructed as-needed -- the entire corpus is
    never stored in memory at once.

    The constructor to C{StreamBackedCorpusView} takes two arguments:
    a corpus filename; and a block reader.  A X{block reader} is a
    function that reads and reads zero or more tokens from a stream,
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
    larger block sizes may decrase performance for random access to
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
        lifetime of the C{CorpusView}, then the C{CorpusView}'s beahvior
        is undefined.

    @ivar _block_reader: The function used to read 
        a single block from the underlying file stream.
    @ivar _toknum: A list containing the token index of each block
        that has been process.  In particular, C{_toknum[i]} is the
        token index of the first token in block C{i}.  Together
        with L{_filepos}, this forms a partial mapping between token
        indices and file positions.
    @ivar _filepos: A list containing the file position of each block
        that has been process.  In particular, C{_toknum[i]} is the
        file position of the first character in block C{i}.  Together
        with L{_toknum}, this forms a partial mapping between token
        indices and file positions.
    @ivar _stream: The stream used to access the underlying corpus
        file.
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
    def __init__(self, filename, block_reader=None):
        """
        Create a new corpus view, based on the file C{filename}, and
        read with C{block_reader}.  See the class documentation
        for more information.
        """
        if block_reader:
            self.read_block = block_reader
        # Initialize our toknum/filepos mapping.
        self._toknum = [0]
        self._filepos = [0]
        # We don't know our length (number of tokens) yet.
        self._len = None
        self._eofpos = None

        self._filename = filename
        self._stream = None
        
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
        self._stream.close()
        self._stream = None

    def __len__(self):
        """
        Return the number of tokens in the corpus file underlying this
        corpus view.
        """
        if self._len is None:
            # iterate_from() sets self._len when it reaches the end
            # of the file:
            for tok in self.iterate_from(self._toknum[-1]): pass
        return self._len
    
    def __getitem__(self, i):
        """
        Return the C{i}th token in the corpus file underlying this
        corpus view.  Negative indices and spans are both supported.
        """
        if isinstance(i, slice):
            start, stop = i.start, i.stop
            # Handle None indices
            if start is None: start = 0
            if stop is None: stop = len(self)
            # Handle negative indices
            if start < 0: start = max(0, len(self)+start)
            if stop < 0: stop = max(0, len(self)+stop)
            # Check if it's in the cache.
            offset = self._cache[0]
            if offset <= start and stop < self._cache[1]:
                return self._cache[2][start-offset:stop-offset]
            # Construct & return the result.
            return list(islice(self.iterate_from(start), stop-start))
        else:
            # Handle negative indices
            if i < 0: i += len(self)
            if i < 0: raise IndexError('index out of range')
            # Check if it's in the cache.
            offset = self._cache[0]
            if offset <= i < self._cache[1]:
                #print 'using cache', self._cache[:2]
                return self._cache[2][i-offset]
            # Use iterate_from to extract it.
            try:
                return self.iterate_from(i).next()
            except StopIteration:
                raise IndexError('index out of range')

    def __iter__(self):
        """
        Return an iterator that generates the tokens in the corpus
        file underlying this corpus view.
        """
        return self.iterate_from(0)

    # If we wanted to be thread-safe, then this method would need to
    # do some locking.
    def iterate_from(self, start_tok):
        """
        Return an iterator that generates the tokens in the corpus
        file underlying this corpus view, starting at the token number
        C{start}.  If C{start>=len(self)}, then this iterator will
        generate no tokens.
        """
        # Decide where in the file we should start.  If `start` is in
        # our mapping, then we can jump streight to the correct block;
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
            assert isinstance(tokens, list) # tokenizer should return list.
            num_toks = len(tokens)
            new_filepos = self._stream.tell()

            # Update our cache.
            self._cache = (toknum, toknum+num_toks, tokens)
            
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

    _MAX_REPR_SIZE = 60
    def __repr__(self):
        """
        @return: A string representation for this corpus view.  The
        representation is similar to a list's representation; but if
        it would be more than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for tok in self:
            pieces.append(repr(tok))
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return '[%s, ...]' % ', '.join(pieces[:-1])
        else:
            return '[%s]' % ', '.join(pieces)

class ConcatenatedCorpusView:
    """
    A 'view' of a corpus file that joins together one or more
    L{StreamBackedCorpusViews<StreamBackedCorpusView>}.  At most
    one file handle is left open at any time.
    """
    def __init__(self, corpus_views):
        self._pieces = corpus_views
        """A list of the corpus subviews that make up this
        concatination."""
        
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
            start, stop = i.start, i.stop
            # Handle None indices
            if start is None: start = 0
            if stop is None: stop = len(self)
            # Handle negative indices
            if start < 0: start = max(0, len(self)+start)
            if stop < 0: stop = max(0, len(self)+stop)
            # Construct & return the result.
            return list(islice(self.iterate_from(start), stop-start))
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
            if (self._open_piece != piece and 
                self._open_piece is not None):
                self._open_piece.close()
                self._open_piece = piece

            # Get everything we can from this piece.
            for tok in piece.iterate_from(start_tok-offset):
                yield tok

            # Update the offset table.
            if piecenum+1 == len(self._offsets):
                self._offsets.append(self._offsets[-1] + len(piece))

            # Move on to the next piece.
            piecenum += 1
            start_tok = self._offsets[piecenum]
        
    _MAX_REPR_SIZE = 60
    def __repr__(self):
        """
        @return: A string representation for this corpus view.  The
        representation is similar to a list's representation; but if
        it would be more than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for tok in self:
            pieces.append(repr(tok))
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return '[%s, ...]' % ', '.join(pieces[:-1])
        else:
            return '[%s]' % ', '.join(pieces)

def concat(docs):
    """
    Concatenate together the contents of multiple documents from a
    single corpus, using an appropriate concatenation function.  This
    utility function is used by corpus readers when the user requests
    more than one document at a time.
    """
    types = set([d.__class__ for d in docs])

    if types.issubset([StreamBackedCorpusView]):
        return ConcatenatedCorpusView(docs)
    
    elif types.issubset([str, unicode, basestring]):
        return reduce((lambda a,b:a+b), docs, '')

    elif types.issubset([list]):
        return reduce((lambda a,b:a+b), docs, [])
    
    elif types.issubset([tuple]):
        return reduce((lambda a,b:a+b), docs, ())
    
    elif len(types) == 1 and ElementTree.iselement(list(types)[0]):
        xmltree = ElementTree.Element('documents')
        for doc in docs: xmltree.append(doc)
        return xmltree

    else:
        raise ValueError("Don't know how to concatenate types: %r" % types)


######################################################################
#{ Finding Corpus Directories & Files
######################################################################

def find_corpus(corpusname):
    corpusname = os.path.join(*corpusname.split('/'))
    for directory in get_corpus_path():
        p = os.path.join(directory, corpusname)
        if os.path.exists(p):
            return p
    print """
        *****************************************************************
          Corpus not found.  For installation instructions, please see
             http://nltk.sourceforge.net/index.php/Installation
        *****************************************************************"""
    raise ValueError('Corpus not found!')

def find_corpus_file(corpusname, filename, extension=None):
    # Look for it in the corpus
    if not os.path.isabs(filename):
        corpusname = os.path.join(*corpusname.split('/'))
        p = os.path.join(find_corpus(corpusname), filename)
        if extension: p += extension
        if os.path.exists(p):
            return p

    # Else check if it's a filename.
    if os.path.exists(filename):
        return filename
    elif extension and os.path.exists(filename+extension):
        return filename+extension

    # Else complain
    raise ValueError('Corpus file %r in %s not found' %
                     (filename, corpusname))
    
######################################################################
#{ Helpers
######################################################################

def read_whitespace_block(stream):
    return stream.readline().split()

def read_wordpunct_block(stream):
    return list(tokenize.wordpunct(stream.readline()))

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

def read_sexpr_block(stream, block_size=10):
    start = stream.tell()
    block = ''
    while True:
        try:
            block += stream.read(block_size)
            tokens, offset = _parse_sexpr_block(block)
            # Skip whitespace
            offset = re.compile(r'\s*').search(block, offset).end()
            # Move to the end position.
            stream.seek(start+offset)
            # Return the list of tokens we processed
            return tokens
        except ValueError, e:
            if e.args[0] == 'Block too small':
                continue
            else: raise

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
            m2 = re.compile(r'[\s()]').search(block, start)
            if m2:
                end = m2.start()
            else:
                if tokens: return tokens, end
                raise ValueError('Block too small')

        # Case 2: parenthasized sexpr.
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
