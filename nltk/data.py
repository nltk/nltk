# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Functions to find and load files in the NLTK data package.

The NLTK data package contains a variety of data files, including
corpora, grammars, and saved processing objects.  This module provides
two functions to find and load these data files: L{find()} searches
for a given resource, and returns its filename; and L{load()} loads a
given resource and adds it to a resource cache.
"""

import sys, os, os.path, pickle, textwrap, weakref, yaml
from nltk.corpus.reader.api import CorpusReader
from nltk import cfg

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
path += [d for d in os.environ.get('NLTK_CORPORA', '').split(':') if d]
path += [d for d in os.environ.get('NLTK_DATA', '').split(':') if d]
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
# Access Functions
######################################################################

_resource_cache = weakref.WeakValueDictionary()
"""A weakref dictionary used to cache resources so that they won't
   need to be loaded more than once."""

def find(resource):
    """
    Find the given resource from the NLTK data package, and return a
    corresponding path name.  If the given resource is not found,
    raise a C{LookupError}, whose message gives a pointer to the
    installation instructions for the NLTK data package.

    @type resource: C{str}
    @param resource: The name of the resource to search for.  Resource
        names are posix-style relative path names, such as
        C{'corpora/brown'}.  In particular, directory names should
        always be separated by the C{'/'} character, which will be
        automatically converted to a platform-appropriate path
        separator.
    @rtype: C{str}
    """
    # Check each directory in our path:
    for directory in path:
        p = os.path.join(directory, os.path.join(*resource.split('/')))
        if os.path.exists(p):
            return p
        
    # Display a friendly error message if the resource wasn't found:
    msg = textwrap.fill(
        'Resource %r not found.  For installation instructions, '
        'please see <http://nltk.org/index.php/Installation>.' %
        (resource,), initial_indent='  ', subsequent_indent='  ', width=66)
    msg += '\n  Searched in:' + ''.join('\n    - %r' % d for d in path)
    sep = '*'*70
    resource_not_found = '\n%s\n%s\n%s' % (sep, msg, sep)
    raise LookupError(resource_not_found)

def load(resource, format='auto', cache=True, verbose=False):
    """
    Load a given resource from the NLTK resource package.  The following
    resource formats are currently supported:
      - C{'pickle'}
      - C{'yaml'}
      - C{'cfg'}
      - C{'pcfg'}
      - C{'fcfg'}

    If no format is specified, C{load()} will attempt to determine a
    format based on the resource name's file extension.  If that
    fails, C{load()} will raise a C{ValueError} exception.

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
        resource_val = _resource_cache.get(resource)
        if resource_val is not None:
            return resource_val
    
    # This will raise an exception if we can't find the resource:
    filename = find(resource)

    # Let the user know what's going on.
    if verbose:
        print '<<Loading %s>>' % (resource,)

    # Determine the format of the resource.
    if format == 'auto':
        if filename.endswith('.pickle'): format = 'pickle'
        if filename.endswith('.yaml'): format = 'yaml'
        if filename.endswith('.cfg'): format = 'cfg'
        if filename.endswith('.pcfg'): format = 'pcfg'
        if filename.endswith('.fcfg'): format = 'fcfg'
        
    # Load the resource.
    if format == 'pickle':
        resource_val = pickle.load(open(filename, 'rb'))
    elif format == 'yaml':
        resource_val = yaml.load(open(filename, 'rb'))
    elif format == 'cfg':
        resource_val = cfg.parse_cfg(open(filename, 'r').read())
    elif format == 'pcfg':
        resource_val = cfg.parse_pcfg(open(filename, 'r').read())
    elif format == 'fcfg':
        # NB parse_fcfg returns a FeatGramLex -- a tuple (grammar, lexicon)
        resource_val = cfg.parse_fcfg(open(filename, 'r').read())
    else:
        raise ValueError('Unknown format type!')

    # If requested, add it to the cache.
    if cache:
        _resource_cache[resource] = resource_val
    
    return resource_val

def clear_cache():
    """
    Remove all objects from the resource cache.
    @see: L{load()}
    """
    _resource_cache.clear()

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

######################################################################
#{ Lazy Corpus Loader
######################################################################

class LazyCorpusLoader(object):
    """
    A proxy object which is used to stand in for a corpus object
    before the corpus is loaded.  This allows NLTK to create an object
    for each corpus, but defer the costs associated with loading those
    corpora until the first time that they're actually accessed.

    The first time this object is accessed in any way, it will load
    the corresponding corpus, and transform itself into that corpus
    (by modifying its own C{__class__} and C{__dict__} attributes).

    If the corpus can not be found, then accessing this object will
    raise an exception, displaying installation instructions for the
    NLTK data package.  Once they've properly installed the data
    package (or modified C{nltk.data.path} to point to its location),
    they can then use the corpus object without restarting python.
    """
    def __init__(self, name, reader_cls, *args, **kwargs):
        assert issubclass(reader_cls, CorpusReader)
        self.__name = name
        self.__reader_cls = reader_cls
        self.__args = args
        self.__kwargs = kwargs

    def __load(self):
        # Find the corpus root directory, and load the corpus.
        root = find('corpora/' + self.__name)
        corpus = self.__reader_cls(root, *self.__args, **self.__kwargs)
        
        # This is where the magic happens!  Transform ourselves into
        # the corpus by modifying our own __dict__ and __class__ to
        # match that of the corpus.
        self.__dict__ = corpus.__dict__
        self.__class__ = corpus.__class__

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

