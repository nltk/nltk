# Natural Language Toolkit: Corpus Reader Utilities
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os, sys, bisect

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
    A base class for defining a 'view' for a corpus file.  A
    C{StreamBackedCorpusView} object acts like a sequence of tokens:
    it can be accessed by index, iterated over, etc.  However, the
    tokens are only constructed as-needed.

    The constructor to C{StreamBackedCorpusView} takes two arguments:
    a corpus file (which can be either a filename or a stream); and a
    block tokenizer.  A X{block tokenizer} is a function that reads
    and tokenizes zero or more tokens from a stream, and returns them
    as a list.  A very simple example of a block tokenizer is:

        >>> def simple_block_tokenizer(stream):
        ...     return stream.readline().split()

    This simple block tokenizer reads a single line at a time, and
    returns a single token (consisting of a string) for each
    whitespace-separated substring on the line.

    When deciding how to define the block tokenizer for a given
    corpus, careful consideration should be given to the size of
    blocks handled by the block tokenizer.  Smaller block sizes will
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
         index, it tokenizes one block at a time using the block
         tokenizer, until it reaches the requested token.

    The toknum/filepos mapping is created lazily: it is initially
    empty, but every time a new block is tokenized, the block's
    initial token is added to the mapping.  (Thus, the toknum/filepos
    map has one entry per block.)

    In order to increase efficiency for random access patterns that
    have high degrees of locality, the corpus view may cache one or
    more tokenized blocks.

    @note: Each C{CorpusView} object internally maintains an open file
        object for its underlying corpus file.  This file should be
	automatically closed when the C{CorpusView} is garbage collected,
	but if you wish to close it manually, use the L{close()}
	method.  If you access a C{CorpusView}'s items after it has been
	closed, the file object will be automatically re-opened.
	
    @warning: If the contents of the file are modified during the
        lifetime of the C{CorpusView}, then the C{CorpusView}'s beahvior
	is undefined.

    @ivar _block_tokenizer: The function used to read and tokenize
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
    @ivar _cache: A cache of the most recently tokenized block.  It
       is encoded as a tuple (start_toknum, end_toknum, tokens), where
       start_toknum is the token index of the first token in the block;
       end_toknum is the token index of the first token not in the
       block; and tokens is a list of the tokens in the block.
    """
    def __init__(self, corpus_file, block_tokenizer=None):
        """
        Create a new corpus view, based on the file C{corpus_file}, and
        tokenized with C{block_tokenizer}.  See the class documentation
        for more information.
        """
        if block_tokenizer:
            self._block_tokenizer = block_tokenizer
        # Initialize our toknum/filepos mapping.
	self._toknum = [0]
	self._filepos = [0]
        # We don't know our length (number of tokens) yet.
	self._len = None
        # Initialize our input stream.
        if isinstance(corpus_file, basestring):
            self._stream = open(corpus_file, 'r')
        else:
            self._stream = corpus_file
        # Find the character position of the end of the file.
        self._stream.seek(0, 2)
        self._eofpos = self._stream.tell()
        # Maintain a cache of the most recently tokenized block, to
        # increase efficiency of random access.
        self._cache = (-1, -1, None)

    def _block_tokenizer(self, stream):
        return self.tokenize_block(stream)

    def close(self):
	"""
	Close the file stream associated with this corpus view.  This
	can be useful if you are worried about running out of file
	handles (although the stream should automatically be closed
	upon garbage collection of the corpus view).  The corpus view
	should not be used after it is closed -- doing so will raise
	C{IOError}s or C{OSError}s.
	"""
	self._stream.close()

    def __len__(self):
	"""
	Return the number of tokens in the corpus file underlying this
	corpus view.
	"""
	if self._len is None:
	    # _iterate_from() sets self._len when it reaches the end
	    # of the file:
	    for tok in self._iterate_from(self._toknum[-1]): pass
	return self._len
    
    def __getitem__(self, i):
	"""
	Return the C{i}th token in the corpus file underlying this
	corpus view.  Negative indices and spans are both supported.
	"""
	if isinstance(i, slice):
	    start, stop = i.start, i.stop
            # Handle negative indices
	    if start < 0: start = max(0, len(self)+start)
	    if stop < 0: stop = max(0, len(self)+stop)
            # Check if it's n the cache.
            offset = self._cache[0]
            if offset <= start and stop < self._cache[1]:
                return self._cache[2][start-offset:stop-offset]
            # Construct & return the result.
	    result = []
	    for i,tok in enumerate(self._iterate_from(start)):
		if i+start >= stop: return result
		result.append(tok)
	    return result
	else:
            # Handle negative indices
	    if i < 0: i = max(0, len(self)+i)
            # Check if it's in the cache.
            offset = self._cache[0]
            if offset <= i < self._cache[1]:
                #print 'using cache', self._cache[:2]
                return self._cache[2][i-offset]
            # Use _iterate_from to extract it.
	    try:
		return self._iterate_from(i).next()
	    except StopIteration:
		raise KeyError(i)

    def __iter__(self):
	"""
	Return an iterator that generates the tokens in the corpus
	file underlying this corpus view.
	"""
	return self._iterate_from(0)

    # If we wanted to be thread-safe, then this method would need to
    # do some locking.
    def _iterate_from(self, start_tok):
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

        # Each iteration through this loop, we tokenize a single block
        # from the stream.
	while True:
	    # Tokenize the next block.
	    self._stream.seek(filepos)
	    tokens = self._block_tokenizer(self._stream)
            assert isinstance(tokens, list) # tokenzier should return list.
	    num_toks = len(tokens)
            # Update our cache.
            self._cache = (toknum, toknum+len(tokens), tokens)
	    # Update our mapping.
	    if num_toks+toknum > self._toknum[-1]:
		assert num_toks > 0 # is this always true here?
		self._filepos.append(self._stream.tell())
		self._toknum.append(toknum+num_toks)
	    # Generate the tokens in this block (but skip any tokens
	    # before start_tok).  Note that between yields, our state
	    # may be modified.
	    for tok in tokens[max(0, start_tok-toknum):]:
		yield tok
	    # Update our indices
	    toknum += len(tokens)
	    filepos = self._stream.tell()
            # If we're at the end of the file, then we're done; set
            # our length and terminate the generator.
            if filepos == self._eofpos:
		self._len = toknum
		return

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
    elif os.path.exists(filename+extension):
        return filename+extension

    # Else complain
    raise ValueError('Corpus file %r in %s not found' %
                     (filename, corpusname))
    
######################################################################
#{ Helpers
######################################################################
import re

def tokenize_sexpr(stream, block_size=10):
    start = stream.tell()
    block = ''
    while True:
        try:
            block += stream.read(block_size)
            tokens, offset = tokenize_sexpr_block(block)
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

def tokenize_sexpr_block(block):
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
    
