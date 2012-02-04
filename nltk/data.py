# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Functions to find and load NLTK resource files, such as corpora,
grammars, and saved processing objects.  Resource files are identified
using URLs, such as ``nltk:corpora/abc/rural.txt`` or
``http://nltk.org/sample/toy.cfg``.  The following URL protocols are
supported:

  - ``file:path``: Specifies the file whose path is *path*.
    Both relative and absolute paths may be used.

  - ``http://host/path``: Specifies the file stored on the web
    server *host* at path *path*.

  - ``nltk:path``: Specifies the file stored in the NLTK data
    package at *path*.  NLTK will search for these files in the
    directories specified by ``nltk.data.path``.

If no protocol is specified, then the default protocol ``nltk:`` will
be used.

This module provides to functions that can be used to access a
resource file, given its URL: ``load()`` loads a given resource, and
adds it to a resource cache; and ``retrieve()`` copies a given resource
to a local file.
"""

import sys
import os, os.path
import textwrap
import weakref
import re
import urllib2
import zipfile
import codecs

from gzip import GzipFile, READ as GZ_READ, WRITE as GZ_WRITE

try:
    from zlib import Z_SYNC_FLUSH as FLUSH
except:
    from zlib import Z_FINISH as FLUSH

try:
    import cPickle as pickle
except:
    import pickle

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

import nltk

######################################################################
# Search Path
######################################################################

path = []
"""A list of directories where the NLTK data package might reside.
   These directories will be checked in order when looking for a
   resource in the data package.  Note that this allows users to
   substitute in their own versions of resources, if they have them
   (e.g., in their home directory under ~/nltk_data)."""

# User-specified locations:
path += [d for d in os.environ.get('NLTK_DATA', '').split(os.pathsep) if d]
if os.path.expanduser('~/') != '~/': path += [
    os.path.expanduser('~/nltk_data')]

# Common locations on Windows:
if sys.platform.startswith('win'): path += [
    r'C:\nltk_data', r'D:\nltk_data', r'E:\nltk_data',
    os.path.join(sys.prefix, 'nltk_data'),
    os.path.join(sys.prefix, 'lib', 'nltk_data'),
    os.path.join(os.environ.get('APPDATA', 'C:\\'), 'nltk_data')]

# Common locations on UNIX & OS X:
else: path += [
    '/usr/share/nltk_data',
    '/usr/local/share/nltk_data',
    '/usr/lib/nltk_data',
    '/usr/local/lib/nltk_data']

######################################################################
# Path Pointers
######################################################################

class PathPointer(object):
    """
    An abstract base class for 'path pointers,' used by NLTK's data
    package to identify specific paths.  Two subclasses exist:
    ``FileSystemPathPointer`` identifies a file that can be accessed
    directly via a given absolute path.  ``ZipFilePathPointer``
    identifies a file contained within a zipfile, that can be accessed
    by reading that zipfile.
    """
    def open(self, encoding=None):
        """
        Return a seekable read-only stream that can be used to read
        the contents of the file identified by this path pointer.

        :raise IOError: If the path specified by this pointer does
            not contain a readable file.
        """
        raise NotImplementedError('abstract base class')

    def file_size(self):
        """
        Return the size of the file pointed to by this path pointer,
        in bytes.

        :raise IOError: If the path specified by this pointer does
            not contain a readable file.
        """
        raise NotImplementedError('abstract base class')

    def join(self, fileid):
        """
        Return a new path pointer formed by starting at the path
        identified by this pointer, and then following the relative
        path given by ``fileid``.  The path components of ``fileid``
        should be seperated by forward slashes, regardless of
        the underlying file system's path seperator character.
        """
        raise NotImplementedError('abstract base class')


class FileSystemPathPointer(PathPointer, str):
    """
    A path pointer that identifies a file which can be accessed
    directly via a given absolute path.  ``FileSystemPathPointer`` is a
    subclass of ``str`` for backwards compatibility purposes --
    this allows old code that expected ``nltk.data.find()`` to expect a
    string to usually work (assuming the resource is not found in a
    zipfile).  It also permits ``open()`` to work on a ``FileSystemPathPointer``.

    """
    def __init__(self, path):
        """
        Create a new path pointer for the given absolute path.

        :raise IOError: If the given path does not exist.
        """
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise IOError('No such file or directory: %r' % path)
        self._path = path

        # There's no need to call str.__init__(), since it's a no-op;
        # str does all of its setup work in __new__.

    @property
    def path(self):
        """The absolute path identified by this path pointer."""
        return self._path

    def open(self, encoding=None):
        stream = open(self._path, 'rb')
        if encoding is not None:
            stream = SeekableUnicodeStreamReader(stream, encoding)
        return stream

    def file_size(self):
        return os.stat(self._path).st_size

    def join(self, fileid):
        path = os.path.join(self._path, *fileid.split('/'))
        return FileSystemPathPointer(path)

    def __repr__(self):
        return 'FileSystemPathPointer(%r)' % self._path

    def __str__(self):
        return self._path


class BufferedGzipFile(GzipFile):
    """
    A ``GzipFile`` subclass that buffers calls to ``read()`` and ``write()``.
    This allows faster reads and writes of data to and from gzip-compressed
    files at the cost of using more memory.

    The default buffer size is 2MB.

    ``BufferedGzipFile`` is useful for loading large gzipped pickle objects
    as well as writing large encoded feature files for classifier training.
    """
    SIZE = 2 * 2**20

    def __init__(self, filename=None, mode=None, compresslevel=9,
                 fileobj=None, **kwargs):
        """
        Return a buffered gzip file object.

        :param filename: a filesystem path
        :type filename: str
        :param mode: a file mode which can be any of 'r', 'rb', 'a', 'ab',
            'w', or 'wb'
        :type mode: str
        :param compresslevel: The compresslevel argument is an integer from 1
            to 9 controlling the level of compression; 1 is fastest and
            produces the least compression, and 9 is slowest and produces the
            most compression. The default is 9.
        :type compresslevel: int
        :param fileobj: a StringIO stream to read from instead of a file.
        :type fileobj: StringIO
        :param size: number of bytes to buffer during calls to read() and write()
        :type size: int
        :rtype: BufferedGzipFile
        """
        GzipFile.__init__(self, filename, mode, compresslevel, fileobj)
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

    def flush(self, lib_mode=FLUSH):
        self._buffer.flush()
        GzipFile.flush(self, lib_mode)

    def read(self, size=None):
        if not size:
            size = self._size
            contents = StringIO()
            while True:
                blocks = GzipFile.read(self, size)
                if not blocks:
                    contents.flush()
                    break
                contents.write(blocks)
            return contents.getvalue()
        else:
            return GzipFile.read(self, size)

    def write(self, data, size=-1):
        """
        :param data: str to write to file or buffer
        :type data: str
        :param size: buffer at least size bytes before writing to file
        :type size: int
        """
        if not size:
            size = self._size
        if self._len + len(data) <= size:
            self._write_buffer(data)
        else:
            self._write_gzip(data)


class GzipFileSystemPathPointer(FileSystemPathPointer):
    """
    A subclass of ``FileSystemPathPointer`` that identifies a gzip-compressed
    file located at a given absolute path.  ``GzipFileSystemPathPointer`` is
    appropriate for loading large gzip-compressed pickle objects efficiently.
    """
    def open(self, encoding=None):
        stream = BufferedGzipFile(self._path, 'rb')
        if encoding:
            stream = SeekableUnicodeStreamReader(stream, encoding)
        return stream


class ZipFilePathPointer(PathPointer):
    """
    A path pointer that identifies a file contained within a zipfile,
    which can be accessed by reading that zipfile.
    """
    def __init__(self, zipfile, entry=''):
        """
        Create a new path pointer pointing at the specified entry
        in the given zipfile.

        :raise IOError: If the given zipfile does not exist, or if it
        does not contain the specified entry.
        """
        if isinstance(zipfile, basestring):
            zipfile = OpenOnDemandZipFile(os.path.abspath(zipfile))

        # Normalize the entry string:
        entry = re.sub('(^|/)/+', r'\1', entry)

        # Check that the entry exists:
        if entry:
            try: zipfile.getinfo(entry)
            except:
                # Sometimes directories aren't explicitly listed in
                # the zip file.  So if `entry` is a directory name,
                # then check if the zipfile contains any files that
                # are under the given directory.
                if (entry.endswith('/') and
                    [n for n in zipfile.namelist() if n.startswith(entry)]):
                    pass # zipfile contains a file in that directory.
                else:
                    # Otherwise, complain.
                    raise IOError('Zipfile %r does not contain %r' %
                                  (zipfile.filename, entry))
        self._zipfile = zipfile
        self._entry = entry

    @property
    def zipfile(self): 
        """
        The zipfile.ZipFile object used to access the zip file
        containing the entry identified by this path pointer.
        """
        return self._zipfile

    @property
    def entry(self):
        """
        The name of the file within zipfile that this path
        pointer points to.
        """
        return self._entry

    def open(self, encoding=None):
        data = self._zipfile.read(self._entry)
        stream = StringIO(data)
        if self._entry.endswith('.gz'):
            stream = BufferedGzipFile(self._entry, fileobj=stream)
        elif encoding is not None:
            stream = SeekableUnicodeStreamReader(stream, encoding)
        return stream

    def file_size(self):
        return self._zipfile.getinfo(self._entry).file_size

    def join(self, fileid):
        entry = '%s/%s' % (self._entry, fileid)
        return ZipFilePathPointer(self._zipfile, entry)

    def __repr__(self):
        return 'ZipFilePathPointer(%r, %r)' % (
            self._zipfile.filename, self._entry)

    def __str__(self):
        return '%r/%r' % (self._zipfile.filename, self._entry)

######################################################################
# Access Functions
######################################################################

# Don't use a weak dictionary, because in the common case this
# causes a lot more reloading that necessary.
_resource_cache = {}
"""A dictionary used to cache resources so that they won't
   need to be loaded more than once."""

def find(resource_name):
    """
    Find the given resource by searching through the directories and
    zip files in ``nltk.data.path``, and return a corresponding path
    name.  If the given resource is not found, raise a ``LookupError``,
    whose message gives a pointer to the installation instructions for
    the NLTK downloader.

    Zip File Handling:

      - If ``resource_name`` contains a component with a ``.zip``
        extension, then it is assumed to be a zipfile; and the
        remaining path components are used to look inside the zipfile.

      - If any element of ``nltk.data.path`` has a ``.zip`` extension,
        then it is assumed to be a zipfile.

      - If a given resource name that does not contain any zipfile
        component is not found initially, then ``find()`` will make a
        second attempt to find that resource, by replacing each
        component *p* in the path with *p.zip/p*.  For example, this
        allows ``find()`` to map the resource name
        ``corpora/chat80/cities.pl`` to a zip file path pointer to
        ``corpora/chat80.zip/chat80/cities.pl``.

      - When using ``find()`` to locate a directory contained in a
        zipfile, the resource name must end with the forward slash
        character.  Otherwise, ``find()`` will not locate the
        directory.

    :type resource_name: str
    :param resource_name: The name of the resource to search for.
        Resource names are posix-style relative path names, such as
        ``corpora/brown``.  In particular, directory names should always
        be separated by the forward slash character, which will be
        automatically converted to a platform-appropriate path separator.
    :rtype: str
    """
    # Check if the resource name includes a zipfile name
    m = re.match('(.*\.zip)/?(.*)$|', resource_name)
    zipfile, zipentry = m.groups()

    # Check each item in our path
    for path_item in path:

        # Is the path item a zipfile?
        if os.path.isfile(path_item) and path_item.endswith('.zip'):
            try: return ZipFilePathPointer(path_item, resource_name)
            except IOError: continue # resource not in zipfile

        # Is the path item a directory?
        elif os.path.isdir(path_item):
            if zipfile is None:
                p = os.path.join(path_item, *resource_name.split('/'))
                if os.path.exists(p):
                    if p.endswith('.gz'):
                        return GzipFileSystemPathPointer(p)
                    else:
                        return FileSystemPathPointer(p)
            else:
                p = os.path.join(path_item, *zipfile.split('/'))
                if os.path.exists(p):
                    try: return ZipFilePathPointer(p, zipentry)
                    except IOError: continue # resource not in zipfile

    # Fallback: if the path doesn't include a zip file, then try
    # again, assuming that one of the path components is inside a
    # zipfile of the same name.
    if zipfile is None:
        pieces = resource_name.split('/')
        for i in range(len(pieces)):
            modified_name = '/'.join(pieces[:i]+[pieces[i]+'.zip']+pieces[i:])
            try: return find(modified_name)
            except LookupError: pass

    # Display a friendly error message if the resource wasn't found:
    msg = textwrap.fill(
        'Resource %r not found.  Please use the NLTK Downloader to '
        'obtain the resource:  >>> nltk.download()' %
        (resource_name,), initial_indent='  ', subsequent_indent='  ',
        width=66)
    msg += '\n  Searched in:' + ''.join('\n    - %r' % d for d in path)
    sep = '*'*70
    resource_not_found = '\n%s\n%s\n%s' % (sep, msg, sep)
    raise LookupError(resource_not_found)

def retrieve(resource_url, filename=None, verbose=True):
    """
    Copy the given resource to a local file.  If no filename is
    specified, then use the URL's filename.  If there is already a
    file named ``filename``, then raise a ``ValueError``.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    """
    if filename is None:
        if resource_url.startswith('file:'):
            filename = os.path.split(filename)[-1]
        else:
            filename = re.sub(r'(^\w+:)?.*/', '', resource_url)
    if os.path.exists(filename):
        filename = os.path.abspath(filename)
        raise ValueError, "File %r already exists!" % filename

    if verbose:
        print 'Retrieving %r, saving to %r' % (resource_url, filename)

    # Open the input & output streams.
    infile = _open(resource_url)
    outfile = open(filename, 'wb')

    # Copy infile -> outfile, using 64k blocks.
    while True:
        s = infile.read(1024*64) # 64k blocks.
        outfile.write(s)
        if not s: break

    # Close both files.
    infile.close()
    outfile.close()

#: A dictionary describing the formats that are supported by NLTK's
#: load() method.  Keys are format names, and values are format
#: descriptions.
FORMATS = {
    'pickle': "A serialized python object, stored using the pickle module.",
    'yaml': "A serialized python object, stored using the yaml module.",
    'cfg': "A context free grammar, parsed by nltk.parse_cfg().",
    'pcfg': "A probabilistic CFG, parsed by nltk.parse_pcfg().",
    'fcfg': "A feature CFG, parsed by nltk.parse_fcfg().",
    'fol': "A list of first order logic expressions, parsed by "
            "nltk.sem.parse_fol() using nltk.sem.logic.LogicParser.",
    'logic': "A list of first order logic expressions, parsed by "
            "nltk.sem.parse_logic().  Requires an additional logic_parser "
            "parameter",
    'val': "A semantic valuation, parsed by nltk.sem.parse_valuation().",
    'raw': "The raw (byte string) contents of a file.",
    }

#: A dictionary mapping from file extensions to format names, used
#: by load() when format="auto" to decide the format for a
#: given resource url.
AUTO_FORMATS = {
    'pickle': 'pickle',
    'yaml': 'yaml',
    'cfg': 'cfg',
    'pcfg': 'pcfg',
    'fcfg': 'fcfg',
    'fol': 'fol',
    'logic': 'logic',
    'val': 'val'}

def load(resource_url, format='auto', cache=True, verbose=False,
         logic_parser=None, fstruct_parser=None):
    """
    Load a given resource from the NLTK data package.  The following
    resource formats are currently supported:

      - ``pickle``
      - ``yaml``
      - ``cfg`` (context free grammars)
      - ``pcfg`` (probabilistic CFGs)
      - ``fcfg`` (feature-based CFGs)
      - ``fol`` (formulas of First Order Logic)
      - ``logic`` (Logical formulas to be parsed by the given logic_parser)
      - ``val`` (valuation of First Order Logic model)
      - ``raw``

    If no format is specified, ``load()`` will attempt to determine a
    format based on the resource name's file extension.  If that
    fails, ``load()`` will raise a ``ValueError`` exception.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    :type cache: bool
    :param cache: If true, add this resource to a cache.  If load()
        finds a resource in its cache, then it will return it from the
        cache rather than loading it.  The cache uses weak references,
        so a resource wil automatically be expunged from the cache
        when no more objects are using it.
    :type verbose: bool
    :param verbose: If true, print a message when loading a resource.
        Messages are not displayed when a resource is retrieved from
        the cache.
    :type logic_parser: LogicParser
    :param logic_parser: The parser that will be used to parse logical
        expressions.
    :type fstruct_parser: FeatStructParser
    :param fstruct_parser: The parser that will be used to parse the
        feature structure of an fcfg.
    """
    # If we've cached the resource, then just return it.
    if cache:
        resource_val = _resource_cache.get(resource_url)
        if resource_val is not None:
            if verbose:
                print '<<Using cached copy of %s>>' % (resource_url,)
            return resource_val

    # Let the user know what's going on.
    if verbose:
        print '<<Loading %s>>' % (resource_url,)

    # Determine the format of the resource.
    if format == 'auto':
        resource_url_parts = resource_url.split('.')
        ext = resource_url_parts[-1]
        if ext == 'gz':
            ext = resource_url_parts[-2]
        format = AUTO_FORMATS.get(ext)
        if format is None:
            raise ValueError('Could not determine format for %s based '
                             'on its file\nextension; use the "format" '
                             'argument to specify the format explicitly.'
                             % resource_url)

    # Load the resource.
    if format == 'pickle':
        resource_val = pickle.load(_open(resource_url))
    elif format == 'yaml':
        import yaml
        resource_val = yaml.load(_open(resource_url))
    elif format == 'cfg':
        resource_val = nltk.grammar.parse_cfg(_open(resource_url).read())
    elif format == 'pcfg':
        resource_val = nltk.grammar.parse_pcfg(_open(resource_url).read())
    elif format == 'fcfg':
        resource_val = nltk.grammar.parse_fcfg(_open(resource_url).read(),
                                      logic_parser=logic_parser,
                                      fstruct_parser=fstruct_parser)
    elif format == 'fol':
        resource_val = nltk.sem.parse_logic(_open(resource_url).read(),
                                       logic_parser=nltk.sem.logic.LogicParser())
    elif format == 'logic':
        resource_val = nltk.sem.parse_logic(_open(resource_url).read(),
                                       logic_parser=logic_parser)
    elif format == 'val':
        resource_val = nltk.sem.parse_valuation(_open(resource_url).read())
    elif format == 'raw':
        resource_val = _open(resource_url).read()
    else:
        assert format not in FORMATS
        raise ValueError('Unknown format type!')

    # If requested, add it to the cache.
    if cache:
        try:
            _resource_cache[resource_url] = resource_val
        except TypeError:
            # We can't create weak references to some object types, like
            # strings and tuples.  For now, just don't cache them.
            pass

    return resource_val

def show_cfg(resource_url, escape='##'):
    """
    Write out a grammar file, ignoring escaped and empty lines.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    :type escape: str
    :param escape: Prepended string that signals lines to be ignored
    """
    resource_val = load(resource_url, format='raw', cache=False)
    lines = resource_val.splitlines()
    for l in lines:
        if l.startswith(escape): continue
        if re.match('^$', l): continue
        print l


def clear_cache():
    """
    Remove all objects from the resource cache.
    :see: load()
    """
    _resource_cache.clear()

def _open(resource_url):
    """
    Helper function that returns an open file object for a resource,
    given its resource URL.  If the given resource URL uses the "nltk:"
    protocol, or uses no protocol, then use ``nltk.data.find`` to find
    its path, and open it with the given mode; if the resource URL
    uses the 'file' protocol, then open the file with the given mode;
    otherwise, delegate to ``urllib2.urlopen``.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    """
    # Divide the resource name into "<protocol>:<path>".
    protocol, path = re.match('(?:(\w+):)?(.*)', resource_url).groups()

    if protocol is None or protocol.lower() == 'nltk':
        return find(path).open()
    elif protocol.lower() == 'file':
        # urllib might not use mode='rb', so handle this one ourselves:
        return open(path, 'rb')
    else:
        return urllib2.urlopen(resource_url)

######################################################################
# Lazy Resource Loader
######################################################################

class LazyLoader(object):
    def __init__(self, path):
        self.__path = path

    def __load(self):
        resource = load(self.__path)
        # This is where the magic happens!  Transform ourselves into
        # the object by modifying our own __dict__ and __class__ to
        # match that of `resource`.
        self.__dict__ = resource.__dict__
        self.__class__ = resource.__class__

    def __getattr__(self, attr):
        self.__load()
        # This looks circular, but its not, since __load() changes our
        # __class__ to something new:
        return getattr(self, attr)

    def __repr__(self):
        self.__load()
        # This looks circular, but its not, since __load() changes our
        # __class__ to something new:
        return '%r' % self

######################################################################
# Open-On-Demand ZipFile
######################################################################

class OpenOnDemandZipFile(zipfile.ZipFile):
    """
    A subclass of ``zipfile.ZipFile`` that closes its file pointer
    whenever it is not using it; and re-opens it when it needs to read
    data from the zipfile.  This is useful for reducing the number of
    open file handles when many zip files are being accessed at once.
    ``OpenOnDemandZipFile`` must be constructed from a filename, not a
    file-like object (to allow re-opening).  ``OpenOnDemandZipFile`` is
    read-only (i.e. ``write()`` and ``writestr()`` are disabled.
    """
    def __init__(self, filename):
        if not isinstance(filename, basestring):
            raise TypeError('ReopenableZipFile filename must be a string')
        zipfile.ZipFile.__init__(self, filename)
        assert self.filename == filename
        self.close()

    def read(self, name):
        assert self.fp is None
        self.fp = open(self.filename, 'rb')
        value = zipfile.ZipFile.read(self, name)
        self.close()
        return value

    def write(self, *args, **kwargs):
        """:raise NotImplementedError: OpenOnDemandZipfile is read-only"""
        raise NotImplementedError('OpenOnDemandZipfile is read-only')

    def writestr(self, *args, **kwargs):
        """:raise NotImplementedError: OpenOnDemandZipfile is read-only"""
        raise NotImplementedError('OpenOnDemandZipfile is read-only')

    def __repr__(self):
        return 'OpenOnDemandZipFile(%r)' % self.filename

######################################################################
#{ Seekable Unicode Stream Reader
######################################################################

class SeekableUnicodeStreamReader(object):
    """
    A stream reader that automatically encodes the source byte stream
    into unicode (like ``codecs.StreamReader``); but still supports the
    ``seek()`` and ``tell()`` operations correctly.  This is in contrast
    to ``codecs.StreamReader``, which provide *broken* ``seek()`` and
    ``tell()`` methods.

    This class was motivated by ``StreamBackedCorpusView``, which
    makes extensive use of ``seek()`` and ``tell()``, and needs to be
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
        """A buffer used by ``readline()`` to hold characters that have
           been read, but have not yet been returned by ``read()`` or
           ``readline()``.  This buffer consists of a list of unicode
           strings, where each string corresponds to a single line.
           The final element of the list may or may not be a complete
           line.  Note that the existence of a linebuffer makes the
           ``tell()`` operation more complex, because it must backtrack
           to the beginning of the buffer to determine the correct
           file position in the underlying byte stream."""

        self._rewind_checkpoint = 0
        """The file position at which the most recent read on the
           underlying stream began.  This is used, together with
           ``_rewind_numchars``, to backtrack to the beginning of
           ``linebuffer`` (which is required by ``tell()``)."""

        self._rewind_numchars = None
        """The number of characters that have been returned since the
           read that started at ``_rewind_checkpoint``.  This is used,
           together with ``_rewind_checkpoint``, to backtrack to the
           beginning of ``linebuffer`` (which is required by ``tell()``)."""

        self._bom = self._check_bom()
        """The length of the byte order marker at the beginning of
           the stream (or None for no byte order marker)."""

    #/////////////////////////////////////////////////////////////////
    # Read methods
    #/////////////////////////////////////////////////////////////////

    def read(self, size=None):
        """
        Read up to ``size`` bytes, decode them using this reader's
        encoding, and return the resulting unicode string.

        :param size: The maximum number of bytes to read.  If not
            specified, then read as many bytes as possible.
        :type size: int
        :rtype: unicode
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

        :param size: The maximum number of bytes to read.  If no
            newline is encountered before ``size`` bytes have been read,
            then the returned value may not be a complete line of text.
        :type size: int
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

        :rtype: list(unicode)
        :param sizehint: Ignored.
        :param keepends: If false, then strip newlines.
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

    @property
    def closed(self):
        """True if the underlying stream is closed."""
        return self.stream.closed

    @property
    def name(self):
        """The name of the underlying stream."""
        return self.stream.name

    @property
    def mode(self):
        """The mode of the underlying stream."""
        return self.stream.mode

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

        :param offset: A byte count offset.
        :param whence: If 0, then the offset is from the start of the file
            (offset should be positive), if 1, then the offset is from the
            current position (offset may be positive or negative); and if 2,
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
        Move the read pointer forward by ``offset`` characters.
        """
        if offset < 0:
            raise ValueError('Negative offsets are not supported')
        # Clear all buffers.
        self.seek(self.tell())
        # Perform the seek operation.
        self._char_seek_forward(offset)

    def _char_seek_forward(self, offset, est_bytes=None):
        """
        Move the file position forward by ``offset`` characters,
        ignoring all buffers.

        :param est_bytes: A hint, giving an estimate of the number of
            bytes that will be neded to move foward by ``offset`` chars.
            Defaults to ``offset``.
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
        Read up to ``size`` bytes from the underlying stream, decode
        them using this reader's encoding, and return the resulting
        unicode string.  ``linebuffer`` is not included in the result.
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

        Return a tuple ``(chars, num_consumed)``, where ``chars`` is
        the decoded unicode string, and ``num_consumed`` is the
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

                # If we're not strict, then re-process it with our
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

__all__ = ['path', 'PathPointer', 'FileSystemPathPointer', 'BufferedGzipFile',
           'GzipFileSystemPathPointer', 'GzipFileSystemPathPointer',
           'find', 'retrieve', 'FORMATS', 'AUTO_FORMATS', 'load',
           'show_cfg', 'clear_cache', 'LazyLoader', 'OpenOnDemandZipFile',
           'GzipFileSystemPathPointer', 'SeekableUnicodeStreamReader']
