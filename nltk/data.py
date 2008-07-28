# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
Functions to find and load NLTK X{resource files}, such as corpora,
grammars, and saved processing objects.  Resource files are identified
using URLs, such as"C{nltk:corpora/abc/rural.txt}" or
"C{http://nltk.org/sample/toy.cfg}".  The following URL protocols are
supported:

  - "C{file:I{path}}": Specifies the file whose path is C{I{path}}.
    Both relative and absolute paths may be used.
    
  - "C{http://I{host}/{path}}": Specifies the file stored on the web
    server C{I{host}} at path C{I{path}}.
    
  - "C{nltk:I{path}}": Specifies the file stored in the NLTK data
    package at C{I{path}}.  NLTK will search for these files in the
    directories specified by L{nltk.data.path}.

If no protocol is specified, then the default protocol "C{nltk:}" will
be used.
 
This module provides to functions that can be used to access a
resource file, given its URL: L{load()} loads a given resource, and
adds it to a resource cache; and L{retrieve()} copies a given resource
to a local file.
"""

import sys
import os, os.path
import pickle
import textwrap
import weakref
import yaml
import re
import urllib
import zipfile
try: import cStringIO as StringIO
except: import StringIO

from nltk import cfg, sem

######################################################################
# Search Path
######################################################################

path = []
"""A list of directories where the NLTK data package might reside.
   These directories will be checked in order when looking for a
   resource in the data package.  Note that this allows users to
   substitute in their own versions of resources, if they have them
   (e.g., in their home directory under ~/nltk/data)."""

# User-specified locations:
path += [d for d in os.environ.get('NLTK_CORPORA', '').split(os.pathsep) if d]
path += [d for d in os.environ.get('NLTK_DATA', '').split(os.pathsep) if d]
if os.path.expanduser('~/') != '~/': path += [
    os.path.expanduser('~/nltk/data'),
    os.path.expanduser('~/data/nltk')]

# Common locations on Windows:
if sys.platform.startswith('win'): path += [
    r'C:\nltk\data', r'C:\nltk', 
    r'D:\nltk\data', r'D:\nltk', 
    r'E:\nltk\data', r'E:\nltk', 
    os.path.join(sys.prefix, 'nltk'),
    os.path.join(sys.prefix, 'nltk', 'data'),
    os.path.join(sys.prefix, 'lib', 'nltk'),
    os.path.join(sys.prefix, 'lib', 'nltk', 'data')]

# Common locations on UNIX & OS X:
else: path += [
    '/usr/share/nltk',
    '/usr/share/nltk/data',
    '/usr/local/share/nltk',
    '/usr/local/share/nltk/data',
    '/usr/lib/nltk',
    '/usr/lib/nltk/data',
    '/usr/local/lib/nltk',
    '/usr/local/lib/nltk/data']

######################################################################
# Path Pointers
######################################################################

class PathPointer(object):
    """
    An abstract base class for 'path pointers,' used by NLTK's data
    package to identify specific paths.  Two subclasses exist:
    L{FileSystemPathPointer} identifies a file that can be accessed
    directly via a given absolute path.  L{ZipFilePathPointer}
    identifies a file contained within a zipfile, that can be accessed
    by reading that zipfile.
    """
    def open(self, mode='rb', encoding=None):
        """
        Return a seekable read-only stream that can be used to read
        the contents of the file identified by this path pointer.

        @raise IOError: If the path specified by this pointer does
            not contain a readable file.
        """
        raise NotImplementedError('abstract base class')

    def file_size(self):
        """
        Return the size of the file pointed to by this path pointer,
        in bytes.

        @raise IOError: If the path specified by this pointer does
            not contain a readable file.
        """
        raise NotImplementedError('abstract base class')
    
    def join(self, fileid):
        """
        Return a new path pointer formed by starting at the path
        identified by this pointer, and then following the relative
        path given by C{fileid}.  The path components of C{fileid}
        should be seperated by forward slashes (C{/}), regardless of
        the underlying file system's path seperator character.
        """
        raise NotImplementedError('abstract base class')

class FileSystemPathPointer(PathPointer, unicode):
    """
    A path pointer that identifies a file which can be accessed
    directly via a given absolute path.  C{FileSystemPathPointer} is a
    subclass of C{unicode} for backwards compatibility purposes --
    this allows old code that expected C{nltk.data.find()} to expect a
    string to usually work (assuming the resource is not found in a
    zipfile).
    """
    def __init__(self, path):
        """
        Create a new path pointer for the given absolute path.

        @raise IOError: If the given path does not exist.
        """
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise IOError('Path %r does not exist' % path)
        self._path = path
        unicode.__init__(self, path)

    path = property(lambda self: self._path, doc="""
        The absolute path identified by this path pointer.""")

    def open(self, mode='rb', encoding=None):
        if mode is None: mode = 'rb'
        if encoding is None:
            return open(self._path, mode)
        else:
            # [xx] use SeekableUnicodeStreamReader instead??
            return codecs.open(self._path, mode, encoding)

    def file_size(self):
        return os.stat(self._path).st_size

    def join(self, fileid):
        path = os.path.join(self._path, *fileid.split('/'))
        return FileSystemPathPointer(path)

    def __repr__(self):
        return 'FileSystemPathPointer(%r)' % self._path

    def __str__(self):
        return self._path

class ZipFilePathPointer(PathPointer):
    """
    A path pointer that identifies a file contained within a zipfile,
    which can be accessed by reading that zipfile.
    """
    def __init__(self, zipfile, entry=''):
        """
        Create a new path pointer pointing at the specified entry
        in the given zipfile.

        @raise IOError: If the given zipfile does not exist, or if it
        does not contain the specified entry.
        """
        if isinstance(zipfile, basestring):
            zipfile = OpenOnDemandZipFile(os.path.abspath(zipfile))
            
        # Normalize the entry string:
        entry = re.sub('(^|/)/+', r'\1', entry)

        # Check that the entry exists:
        if entry:
            try: zipfile.getinfo(entry)
            except: raise IOError('Zipfile %r does not contain %r' % 
                                  (zipfile.filename, entry))
        self._zipfile = zipfile
        self._entry = entry

    zipfile = property(lambda self: self._zipfile, doc="""
        The C{zipfile.ZipFile} object used to access the zip file
        containing the entry identified by this path pointer.""")
    entry = property(lambda self: self._entry, doc="""
        The name of the file within C{zipfile} that this path
        pointer points to.""")

    def open(self, mode='rb', encoding=None):
        if mode not in ('r', 'rb', 'rU', 'rbU', 'rUb', None):
            raise ValueError('ZipFilePathPointer only supports mode="rb"')
        data = self._zipfile.read(self._entry)
        if encoding: data = data.decode(encoding)
        # [xx] n.b.: ignoring universal newline flag here!
        return StringIO.StringIO(data)

    def file_size(self):
        return self._zipfile.getinfo(self._entry).file_size

    def join(self, fileid):
        entry = '%s/%s' % (self._entry, fileid)
        return ZipFilePathPointer(self._zipfile, entry)
    
    def __repr__(self):
        # tempyhack!:
        if self._entry:
            return repr(self._zipfile.filename[:-4])
        
        return 'ZipFilePathPointer(%r, %r)' % (
            self._zipfile.filename, self._entry)
        

######################################################################
# Access Functions
######################################################################

_resource_cache = weakref.WeakValueDictionary()
"""A weakref dictionary used to cache resources so that they won't
   need to be loaded more than once."""

def find(resource_name):
    """
    Find the given resource from the NLTK data package, and return a
    corresponding path name.  If the given resource is not found,
    raise a C{LookupError}, whose message gives a pointer to the
    installation instructions for the NLTK data package.

    @type resource_name: C{str}
    @param resource_name: The name of the resource to search for.
        Resource names are posix-style relative path names, such as
        C{'corpora/brown'}.  In particular, directory names should
        always be separated by the C{'/'} character, which will be
        automatically converted to a platform-appropriate path
        separator.
    @rtype: C{str}
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

        # Is the path item a path_item?
        elif os.path.isdir(path_item):
            if zipfile is None:
                p = os.path.join(path_item, *resource_name.split('/'))
                if os.path.exists(p):
                    return FileSystemPathPointer(p)
            else:
                p = os.path.join(path_item, *zipfile.split('/'))
                if os.path.exists(p):
                    try: return ZipFilePathPointer(p, zipentry)
                    except IOError: continue # resource not in zipfile

    # Display a friendly error message if the resource wasn't found:
    msg = textwrap.fill(
        'Resource %r not found.  For installation instructions, '
        'please see <http://nltk.org/index.php/Installation>.' %
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
    file named C{filename}, then raise a C{ValueError}.
    
    @type resource_url: C{str}
    @param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is C{"nltk:"}, which searches
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
#: L{load()} method.  Keys are format names, and values are format
#: descriptions.
FORMATS = {
    'pickle': "A serialized python object, stored using the pickle module.",
    'yaml': "A serialzied python object, stored using the yaml module.",
    'cfg': "A context free grammar, parsed by nltk.cfg.parse_cfg().",
    'pcfg': "A probabilistic CFG, parsed by nltk.cfg.parse_pcfg().",
    'fcfg': "A feature CFG, parsed by nltk.cfg.parse_fcfg().",
    'fol': "A list of first order logic expressions, parsed by "
            "nltk.sem.parse_fol().",
    'val': "A semantic valuation, parsed by nltk.sem.parse_valuation().",
    'raw': "The raw (byte string) contents of a file.",
    }

#: A dictionary mapping from file extensions to format names, used
#: by L{load()} when C{format="auto"} to decide the format for a
#: given resource url.
AUTO_FORMATS = {
    'pickle': 'pickle',
    'yaml': 'yaml',
    'cfg': 'cfg',
    'pcfg': 'pcfg',
    'fcfg': 'fcfg',
    'fol': 'fol',
    'val': 'val'}

def load(resource_url, format='auto', cache=True, verbose=False):
    """
    Load a given resource from the NLTK data package.  The following
    resource formats are currently supported:
      - C{'pickle'}
      - C{'yaml'}
      - C{'cfg'} (context free grammars)
      - C{'pcfg'} (probabilistic CFGs)
      - C{'fcfg'} (feature-based CFGs)
      - C{'fol'} (formulas of First Order Logic)
      - C{'val'} (valuation of First Order Logic model)
      - C{'raw'}

    If no format is specified, C{load()} will attempt to determine a
    format based on the resource name's file extension.  If that
    fails, C{load()} will raise a C{ValueError} exception.

    @type resource_url: C{str}
    @param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is C{"nltk:"}, which searches
        for the file in the the NLTK data package.
    @type cache: C{bool}
    @param cache: If true, add this resource to a cache.  If C{load}
        finds a resource in its cache, then it will return it from the
        cache rather than loading it.  The cache uses weak references,
        so a resource wil automatically be expunged from the cache
        when no more objects are using it.
        
    @type verbose: C{bool}
    @param verbose: If true, print a message when loading a resource.
        Messages are not displayed when a resource is retrieved from
        the cache.
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
        ext = resource_url.split('.')[-1]
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
        resource_val = yaml.load(_open(resource_url))
    elif format == 'cfg':
        resource_val = cfg.parse_cfg(_open(resource_url).read())
    elif format == 'pcfg':
        resource_val = cfg.parse_pcfg(_open(resource_url).read())
    elif format == 'fcfg':
        resource_val = cfg.parse_fcfg(_open(resource_url).read())
    elif format == 'fol':
        resource_val = sem.parse_fol(_open(resource_url).read())
    elif format == 'val':
        resource_val = sem.parse_valuation(_open(resource_url).read())
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
    Write out a grammar file, ignoring escaped and empty lines
    @type resource_url: C{str}
    @param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is C{"nltk:"}, which searches
        for the file in the the NLTK data package.
    @type escape: C{str}
    @param escape: Prepended string that signals lines to be ignored
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
    @see: L{load()}
    """
    _resource_cache.clear()

def _open(resource_url, mode='rb'):
    """
    Helper function that returns an open file object for a resource,
    given its resource URL.  If the given resource URL uses the 'ntlk'
    protocol, or uses no protocol, then use L{nltk.data.find} to find
    its path, and open it with the given mode; if the resource URL
    uses the 'file' protocol, then open the file with the given mode;
    otherwise, delegate to C{urllib.urlopen}.
    
    @type resource_url: C{str}
    @param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is C{"nltk:"}, which searches
        for the file in the the NLTK data package.
    """
    # Divide the resource name into "<protocol>:<path>".
    protocol, path = re.match('(?:(\w+):)?(.*)', resource_url).groups()

    if protocol is None or protocol.lower() == 'nltk':
        return find(path).open(mode)
    elif protocol.lower() == 'file':
        # urllib might not use mode='rb', so handle this one ourselves:
        return open(path, mode)
    else:
        return urllib.urlopen(resource_url)

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
# ZipFile subclass
######################################################################

class OpenOnDemandZipFile(zipfile.ZipFile):
    """
    A subclass of C{zipfile.ZipFile} that closes its file pointer
    whenever it is not using it; and re-opens it when it needs to read
    data from the zipfile.  This is useful for reducing the number of
    open file handles when many zip files are being accessed at once.
    C{OpenOnDemandZipFile} must be constructed from a filename, not a
    file-like object (to allow re-opening).  C{OpenOnDemandZipFile} is
    read-only (i.e., C{write} and C{writestr} are disabled.
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
        """@raise NotImplementedError: OpenOnDemandZipfile is read-only"""
        raise NotImplementedError('OpenOnDemandZipfile is read-only')

    def writestr(self, *args, **kwargs):
        """@raise NotImplementedError: OpenOnDemandZipfile is read-only"""
        raise NotImplementedError('OpenOnDemandZipfile is read-only')

    def __repr__(self):
        return 'OpenOnDemandZipFile(%r)' % self.filename
