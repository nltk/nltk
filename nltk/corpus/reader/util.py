# Natural Language Toolkit: Corpus Reader Utilities
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import os, sys, bisect, re, codecs
from itertools import islice
from nltk.corpus.reader.api import CorpusReader
from nltk import tokenize
from nltk.etree import ElementTree
from nltk.internals import deprecated
from nltk.utilities import AbstractLazySequence, LazySubsequence
from nltk.utilities import LazyConcatenation

######################################################################
#{ Corpus View
######################################################################

class StreamBackedCorpusView(AbstractLazySequence):
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

    @warning: If a unicode encoding is specified when constructing a
        C{CorpusView}, then the block reader may only call
        C{stream.seek()} with offsets that have been returned by
        C{stream.tell()}; in particular, calling C{stream.seek()} with
        relative offsets, or with offsets based on string lengths, may
        lead to incorrect behavior.

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
    def __init__(self, filename, block_reader=None, startpos=0,
                 encoding=None):
        """
        Create a new corpus view, based on the file C{filename}, and
        read with C{block_reader}.  See the class documentation
        for more information.

        @param startpos: The file position at which the view will
            start reading.  This can be used to skip over preface
            sections.

        @param encoding: The unicode encoding that should be used to
            read the file's contents.  If no encoding is specified,
            then the file's contents will be read as a non-unicode
            string (i.e., a C{str}).            
        """
        if block_reader:
            self.read_block = block_reader
        # Initialize our toknum/filepos mapping.
        self._toknum = [0]
        self._filepos = [startpos]
        self._encoding = encoding
        # We don't know our length (number of tokens) yet.
        self._len = None

        self._filename = filename
        self._stream = None

        self._current_toknum = None
        """This variable is set to the index of the next token that
           will be read, immediately before L{self.read_block()} is
           called.  This is provided for the benefit of the block
           reader, which under rare circumstances may need to know
           the current token number."""
        
        self._current_blocknum = None
        """This variable is set to the index of the next block that
           will be read, immediately before L{self.read_block()} is
           called.  This is provided for the benefit of the block
           reader, which under rare circumstances may need to know
           the current block number."""
        
        # Find the length of the file.  This also checks that the file
        # exists and is readable & seekable.
        try:
            if self._encoding:
                stream = codecs.open(filename, 'rb', encoding)
            else:
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
        """
        Read a block from the input stream. 

        @return: a block of tokens from the input stream
        @rtype: list of any
        @param stream: an input stream
        @type stream: stream
        """
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
            return LazySubsequence(self, start, stop)
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
            block_index = bisect.bisect_right(self._toknum, start_tok)-1
            toknum = self._toknum[block_index]
            filepos = self._filepos[block_index]
        else:
            block_index = len(self._toknum)-1
            toknum = self._toknum[-1]
            filepos = self._filepos[-1]

        # Open the stream, if it's not open already.
        if self._stream is None:
            if self._encoding:
                self._stream = SeekableUnicodeStreamReader(
                    open(self._filename, 'rb'), self._encoding)
            else:
                self._stream = open(self._filename, 'rb')
            
        # Each iteration through this loop, we read a single block
        # from the stream.
        while True:
            # Read the next block.
            self._stream.seek(filepos)
            self._current_toknum = toknum
            self._current_blocknum = block_index
            tokens = self.read_block(self._stream)
            assert isinstance(tokens, (tuple, list)), \
                   'block reader should return list or tuple.'
            num_toks = len(tokens)
            new_filepos = self._stream.tell()

            # Update our cache.
            self._cache = (toknum, toknum+num_toks, list(tokens))
            
            # Update our mapping.
            assert toknum <= self._toknum[-1]
            if num_toks > 0:
                block_index += 1
                if toknum == self._toknum[-1]:
                    assert new_filepos > self._filepos[-1] # monotonic!
                    self._filepos.append(new_filepos)
                    self._toknum.append(toknum+num_toks)
                else:
                    # Check for consistency:
                    assert new_filepos == self._filepos[block_index], (
                        'inconsistent block reader (num chars read)')
                    assert toknum+num_toks == self._toknum[block_index], (
                        'inconsistent block reader (num tokens returned)')
                    
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

    # Use concat for these, so we can use a ConcatenatedCorpusView
    # when possible.
    def __add__(self, other):
        return concat([self, other])
    def __radd__(self, other):
        return concat([other, self])
    def __mul__(self, count):
        return concat([self] * count)
    def __rmul__(self, count):
        return concat([self] * count)

class ConcatenatedCorpusView(AbstractLazySequence):
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
        if not issubclass(typ, (StreamBackedCorpusView,
                                ConcatenatedCorpusView)):
            break
    else:
        return ConcatenatedCorpusView(docs)

    # If they're all lazy sequences, use a lazy concatenation
    for typ in types:
        if not issubclass(typ, AbstractLazySequence):
            break
    else:
        return LazyConcatenation(docs)

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
    encoding = getattr(stream, 'encoding', None)
    assert encoding is not None or isinstance(block, str)
    if encoding not in (None, 'utf-8'):
        import warnings
        warnings.warn('Parsing may fail, depending on the properties '
                      'of the %s encoding!' % encoding)
        # (e.g., the utf-16 encoding does not work because it insists
        # on adding BOMs to the beginning of encoded strings.)

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
            if encoding is None:
                stream.seek(start+offset)
            else:
                stream.seek(start+len(block[:offset].encode(encoding)))
                
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
    def _parse(self, s):
        raise AssertionError('Abstract method')
    def _word(self, s):
        raise AssertionError('Abstract method')
    def _tag(self, s):
        raise AssertionError('Abstract method')
    def _read_block(self, stream):
        raise AssertionError('Abstract method')

    def raw(self, files=None):
        return concat([codecs.open(path, 'rb', enc).read()
                       for (path,enc) in self.abspaths(files, True)])

    def parsed_sents(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_parsed_sent_block,
                                              encoding=enc)
                       for filename, enc in self.abspaths(files, True)])

    def tagged_sents(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_tagged_sent_block,
                                              encoding=enc)
                       for filename, enc in self.abspaths(files, True)])

    def sents(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_sent_block,
                                              encoding=enc)
                       for filename, enc in self.abspaths(files, True)])

    def tagged_words(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_tagged_word_block,
                                              encoding=enc)
                       for filename, enc in self.abspaths(files, True)])

    def words(self, files=None):
        return concat([StreamBackedCorpusView(filename,
                                              self._read_word_block,
                                              encoding=enc)
                       for filename, enc in self.abspaths(files, True)])

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
            
######################################################################
#{ Seekable Unicode Stream Reader
######################################################################

class SeekableUnicodeStreamReader(object):
    """
    A stream reader that automatically encodes the source byte stream
    into unicode (like C{codecs.StreamReader}); but still supports the
    C{seek()} and C{tell()} operations correctly.  This is in contrast
    to C{codecs.StreamReadedr}, which provide *broken* C{seek()} and
    C{tell()} methods.

    This class was motivated by L{StreamBackedCorpusView}, which
    makes extensive use of C{seek()} and C{tell()}, and needs to be
    able to handle unicode-encoded files.
    
    Note: this class requires stateless decoders.  To my knowledge,
    this shouldn't cause a problem with any of python's builtin
    unicode encodings.
    """
    DEBUG = True #: If true, then perform extra sanity checks.

    def __init__(self, stream, encoding, errors='strict'):
        # Rewind the stream to its beginning.
        stream.seek(0)
        
        self.stream = stream
        """The underlying stream."""
        
        self.encoding = encoding
        """The name of the encoding that should be used to encode the
           underlying stream."""
        
        self.errors = errors
        """The error mode that should be used when decoding data from
           the underlying stream.  Can be 'strict', 'ignore', or
           'replace'."""
        
        self.decode = codecs.getdecoder(encoding)
        """The function that is used to decode byte strings into
           unicode strings."""

        self.bytebuffer = ''
        """A buffer to use bytes that have been read but have not yet
           been decoded.  This is only used when the final bytes from
           a read do not form a complete encoding for a character."""
        
        self.linebuffer = None
        """A buffer used by L{readline()} to hold characters that have
           been read, but have not yet been returned by L{read()} or
           L{readline()}.  This buffer consists of a list of unicode
           strings, where each string corresponds to a single line.
           The final element of the list may or may not be a complete
           line.  Note that the existence of a linebuffer makes the
           L{tell()} operation more complex, because it must backtrack
           to the beginning of the buffer to determine the correct
           file position in the underlying byte stream."""

        self._rewind_checkpoint = 0
        """The file position at which the most recent read on the
           underlying stream began.  This is used, together with
           L{_rewind_numchars}, to backtrack to the beginning of
           L{linebuffer} (which is required by L{tell()})."""
        
        self._rewind_numchars = None
        """The number of characters that have been returned since the
           read that started at L{_rewind_checkpoint}.  This is used,
           together with L{_rewind_checkpoint}, to backtrack to the
           beginning of L{linebuffer} (which is required by
           L{tell()})."""

        self._bom = self._check_bom()
        """The length of the byte order marker at the beginning of
           the stream (or C{None} for no byte order marker)."""

    #/////////////////////////////////////////////////////////////////
    # Read methods
    #/////////////////////////////////////////////////////////////////
    
    def read(self, size=None):
        """
        Read up to C{size} bytes, decode them using this reader's
        encoding, and return the resulting unicode string.

        @param size: The maximum number of bytes to read.  If not
            specified, then read as many bytes as possible.

        @rtype: C{unicode}
        """
        chars = self._read(size)

        # If linebuffer is not empty, then include it in the result
        if self.linebuffer:
            chars = ''.join(self.linebuffer) + chars
            self.linebuffer = None
            self._rewind_numchars = None

        return chars

    def readline(self, size=None):
        """
        Read a line of text, decode it using this reader's encoding,
        and return the resulting unicode string.

        @param size: The maximum number of bytes to read.  If no
            newline is encountered before C{size} bytes have been
            read, then the returned value may not be a complete line
            of text.
        """
        # If we have a non-empty linebuffer, then return the first
        # line from it.  (Note that the last element of linebuffer may
        # not be a complete line; so let _read() deal with it.)
        if self.linebuffer and len(self.linebuffer) > 1:
            line = self.linebuffer.pop(0)
            self._rewind_numchars += len(line)
            return line
        
        readsize = size or 72
        chars = ''

        # If there's a remaining incomplete line in the buffer, add it.
        if self.linebuffer:
            chars += self.linebuffer.pop()
            self.linebuffer = None
        
        while True:
            startpos = self.stream.tell() - len(self.bytebuffer)
            new_chars = self._read(readsize)

            # If we're at a '\r', then read one extra character, since
            # it might be a '\n', to get the proper line ending.  
            if new_chars and new_chars.endswith('\r'):
                new_chars += self._read(1)

            chars += new_chars
            lines = chars.splitlines(True)
            if len(lines) > 1:
                line = lines[0]
                self.linebuffer = lines[1:]
                self._rewind_numchars = len(new_chars)-(len(chars)-len(line))
                self._rewind_checkpoint = startpos
                break
            elif len(lines) == 1:
                line0withend = lines[0]
                line0withoutend = lines[0].splitlines(False)[0]
                if line0withend != line0withoutend: # complete line
                    line = line0withend
                    break
                
            if not new_chars or size is not None:
                line = chars
                break

            # Read successively larger blocks of text.
            if readsize < 8000:
                readsize *= 2

        return line

    def readlines(self, sizehint=None, keepends=True):
        """
        Read this file's contents, decode them using this reader's
        encoding, and return it as a list of unicode lines.

        @rtype: C{list} of C{unicode}
        @param sizehint: Ignored.
        @param keepends: If false, then strip newlines.
        """
        return self.read().splitlines(keepends)

    def next(self):
        """Return the next decoded line from the underlying stream."""
        line = self.readline()
        if line: return line
        else: raise StopIteration

    def __iter__(self):
        """Return self"""
        return self

    def xreadlines(self):
        """Return self"""
        return self

    #/////////////////////////////////////////////////////////////////
    # Pass-through methods & properties
    #/////////////////////////////////////////////////////////////////
    
    closed = property(lambda self: self.stream.closed, doc="""
        True if the underlying stream is closed.""")

    name = property(lambda self: self.stream.name, doc="""
        The name of the underlying stream.""")

    mode = property(lambda self: self.stream.mode, doc="""
        The mode of the underlying stream.""")

    def close(self):
        """
        Close the underlying stream.
        """
        self.stream.close()

    #/////////////////////////////////////////////////////////////////
    # Seek and tell
    #/////////////////////////////////////////////////////////////////
    
    def seek(self, offset, whence=0):
        """
        Move the stream to a new file position.  If the reader is
        maintaining any buffers, tehn they will be cleared.

        @param offset: A byte count offset.
        @param whence: If C{whence} is 0, then the offset is from the
            start of the file (offset should be positive).  If
            C{whence} is 1, then the offset is from the current
            position (offset may be positive or negative); and if 2,
            then the offset is from the end of the file (offset should
            typically be negative).
        """
        if whence == 1:
            raise ValueError('Relative seek is not supported for '
                             'SeekableUnicodeStreamReader -- consider '
                             'using char_seek_forward() instead.')
        self.stream.seek(offset, whence)
        self.linebuffer = None
        self.bytebuffer = ''
        self._rewind_numchars = None
        self._rewind_checkpoint = self.stream.tell()

    def char_seek_forward(self, offset):
        """
        Move the read pointer forward by C{offset} characters.
        """
        if offset < 0:
            raise ValueError('Negative offsets are not supported')
        # Clear all buffers.
        self.seek(self.tell())
        # Perform the seek operation.
        self._char_seek_forward(offset)

    def _char_seek_forward(self, offset, est_bytes=None):
        """
        Move the file position forward by C{offset} characters,
        ignoring all buffers.

        @param est_bytes: A hint, giving an estimate of the number of
            bytes that will be neded to move foward by C{offset} chars.
            Defaults to C{offset}.
        """
        if est_bytes is None: est_bytes = offset
        bytes = ''

        while True:
            # Read in a block of bytes.
            newbytes = self.stream.read(est_bytes-len(bytes))
            bytes += newbytes
                
            # Decode the bytes to characters.
            chars, bytes_decoded = self._incr_decode(bytes)

            # If we got the right number of characters, then seek
            # backwards over any truncated characters, and return.
            if len(chars) == offset:
                self.stream.seek(-len(bytes)+bytes_decoded, 1)
                return

            # If we went too far, then we can back-up until we get it
            # right, using the bytes we've already read.
            if len(chars) > offset:
                while len(chars) > offset:
                    # Assume at least one byte/char.
                    est_bytes += offset-len(chars)
                    chars, bytes_decoded = self._incr_decode(bytes[:est_bytes])
                self.stream.seek(-len(bytes)+bytes_decoded, 1)
                return

            # Otherwise, we haven't read enough bytes yet; loop again.
            est_bytes += offset - len(chars)

    def tell(self):
        """
        Return the current file position on the underlying byte
        stream.  If this reader is maintaining any buffers, then the
        returned file position will be the position of the beginning
        of those buffers.
        """
        # If nothing's buffered, then just return our current filepos:
        if self.linebuffer is None:
            return self.stream.tell() - len(self.bytebuffer)

        # Otherwise, we'll need to backtrack the filepos until we
        # reach the beginning of the buffer.
        
        # Store our original file position, so we can return here.
        orig_filepos = self.stream.tell()

        # Calculate an estimate of where we think the newline is.
        bytes_read = ( (orig_filepos-len(self.bytebuffer)) -
                       self._rewind_checkpoint )
        buf_size = sum([len(line) for line in self.linebuffer])
        est_bytes = (bytes_read * self._rewind_numchars /
                     (self._rewind_numchars + buf_size))

        self.stream.seek(self._rewind_checkpoint)
        self._char_seek_forward(self._rewind_numchars, est_bytes)
        filepos = self.stream.tell()

        # Sanity check
        if self.DEBUG:
            self.stream.seek(filepos)
            check1 = self._incr_decode(self.stream.read(50))[0]
            check2 = ''.join(self.linebuffer)
            assert check1.startswith(check2) or check2.startswith(check1)

        # Return to our original filepos (so we don't have to throw
        # out our buffer.)
        self.stream.seek(orig_filepos)

        # Return the calculated filepos
        return filepos

    #/////////////////////////////////////////////////////////////////
    # Helper methods
    #/////////////////////////////////////////////////////////////////
    
    def _read(self, size=None):
        """
        Read up to C{size} bytes from the underlying stream, decode
        them using this reader's encoding, and return the resulting
        unicode string.  C{linebuffer} is *not* included in the
        result.
        """
        if size == 0: return u''
        
        # Skip past the byte order marker, if present.
        if self._bom and self.stream.tell() == 0:
            self.stream.read(self._bom)
        
        # Read the requested number of bytes.
        if size is None:
            new_bytes = self.stream.read()
        else:
            new_bytes = self.stream.read(size)
        bytes = self.bytebuffer + new_bytes

        # Decode the bytes into unicode characters
        chars, bytes_decoded = self._incr_decode(bytes)
        
        # If we got bytes but couldn't decode any, then read further.
        if (size is not None) and (not chars) and (len(new_bytes) > 0):
            while not chars:
                new_bytes = self.stream.read(1)
                if not new_bytes: break # end of file.
                bytes += new_bytes
                chars, bytes_decoded = self._incr_decode(bytes)
        
        # Record any bytes we didn't consume.
        self.bytebuffer = bytes[bytes_decoded:]

        # Return the result
        return chars
        
    def _incr_decode(self, bytes):
        """
        Decode the given byte string into a unicode string, using this
        reader's encoding.  If an exception is encountered that
        appears to be caused by a truncation error, then just decode
        the byte string without the bytes that cause the trunctaion
        error.

        @return: A tuple C{(chars, num_consumed)}, where C{chars} is
            the decoded unicode string, and C{num_consumed} is the
            number of bytes that were consumed.
        """
        while True:
            try:
                return self.decode(bytes, 'strict')
            except UnicodeDecodeError, exc:
                # If the exception occurs at the end of the string,
                # then assume that it's a truncation error.
                if exc.end == len(bytes):
                    return self.decode(bytes[:exc.start], self.errors)
                
                # Otherwise, if we're being strict, then raise it.
                elif self.errors == 'strict':
                    raise
                
                # If we're not strcit, then re-process it with our
                # errors setting.  This *may* raise an exception.
                else:
                    return self.decode(bytes, self.errors)

    _BOM_TABLE = {
        'utf8': [(codecs.BOM_UTF8, None)],
        'utf16': [(codecs.BOM_UTF16_LE, 'utf16-le'),
                  (codecs.BOM_UTF16_BE, 'utf16-be')],
        'utf16le': [(codecs.BOM_UTF16_LE, None)],
        'utf16be': [(codecs.BOM_UTF16_BE, None)],
        'utf32': [(codecs.BOM_UTF32_LE, 'utf32-le'),
                  (codecs.BOM_UTF32_BE, 'utf32-be')],
        'utf32le': [(codecs.BOM_UTF32_LE, None)],
        'utf32be': [(codecs.BOM_UTF32_BE, None)],
        }

    def _check_bom(self):
        # Normalize our encoding name
        enc = re.sub('[ -]', '', self.encoding.lower())
        
        # Look up our encoding in the BOM table.
        bom_info = self._BOM_TABLE.get(enc)
        
        if bom_info:
            # Read a prefix, to check against the BOM(s)
            bytes = self.stream.read(16)
            self.stream.seek(0)
            
            # Check for each possible BOM.
            for (bom, new_encoding) in bom_info:
                if bytes.startswith(bom):
                    if new_encoding: self.encoding = new_encoding
                    return len(bom)

        return None

