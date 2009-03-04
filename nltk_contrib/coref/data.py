# Natural Language Toolkit (NLTK) Coreference Data Utilities
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from zlib import Z_SYNC_FLUSH
from gzip import GzipFile, READ as GZ_READ, WRITE as GZ_WRITE

try:
    import cPickle as pickle
except:
    import pickle
    
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

class BufferedGzipFile(GzipFile):
    """
    A C{GzipFile} subclass that buffers calls to L{read()} and L{write()}.
    This allows faster reads and writes of data to and from gzip-compressed 
    files at the cost of using more memory.
    
    The default buffer size is 2mb.
    
    C{BufferedGzipFile} is useful for loading large gzipped pickle objects
    as well as writing large encoded feature files for classifier training.
    """    
    SIZE = 2 * 2**20

    def __init__(self, filename=None, mode=None, compresslevel=9, **kwargs):
        """
        @return: a buffered gzip file object
        @rtype: C{BufferedGzipFile}
        @param filename: a filesystem path
        @type filename: C{str}
        @param mode: a file mode which can be any of 'r', 'rb', 'a', 'ab', 
            'w', or 'wb'
        @type mode: C{str}
        @param compresslevel: The compresslevel argument is an integer from 1
            to 9 controlling the level of compression; 1 is fastest and 
            produces the least compression, and 9 is slowest and produces the
            most compression. The default is 9.
        @type compresslevel: C{int}
        @kwparam size: number of bytes to buffer during calls to
            L{read()} and L{write()}
        @type size: C{int}
        """         
        GzipFile.__init__(self, filename, mode, compresslevel)
        self._size = kwargs.get('size', self.SIZE)
        self._buffer = StringIO()
        # cStringIO does not support len.
        self._len = 0
        
    def _reset_buffer(self):
        # For some reason calling StringIO.truncate() here will lead to 
        # inconsistent writes so just set _buffer to a new StringIO object.
        self._buffer = StringIO()
        self._len = 0
        
    def _write_buffer(self, data):
        # Simply write to the buffer and increment the buffer size.
        if data is not None:
            self._buffer.write(data)
            self._len += len(data)
    
    def _write_gzip(self, data):
        # Write the current buffer to the GzipFile.
        GzipFile.write(self, self._buffer.getvalue())
        # Then reset the buffer and write the new data to the buffer.
        self._reset_buffer()
        self._write_buffer(data)

    def close(self):
        # GzipFile.close() doesn't actuallly close anything.
        if self.mode == GZ_WRITE:
            self._write_gzip(None)
            self._reset_buffer()
        return GzipFile.close(self)

    def flush(self, lib_mode=Z_SYNC_FLUSH):
        self._buffer.flush()
        GzipFile.flush(self, lib_mode)

    def read(self, size=None):
        if not size: 
            size = self._size
        return GzipFile.read(self, size)

    def write(self, data, size=None):
        """
        @param data: C{str} to write to file or buffer
        @type data: C{str}
        @param size: buffer at least size bytes before writing to file
        @type size: C{int}
        """
        if not size: 
            size = self._size
        if self._len + len(data) <= size:
            self._write_buffer(data)
        else:
            self._write_gzip(data)