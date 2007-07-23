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

import sys, os, os.path, pickle, textwrap, weakref

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
    '/usr/local/share/nltk/data']

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
    corpus_not_found = '\n%s\n%s\n%s' % (sep, msg, sep)
    raise LookupError(corpus_not_found)

def load(resource, format='auto', cache=True, verbose=False):
    """
    Load a given resource from the NLTK corpus package.  The following
    resource formats are currently supported:
      - C{'pickle'}
      - C{'yaml'}

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
        
    # Load the resource.
    if format == 'pickle':
        resource_val = pickle.load(open(filename, 'rb'))
    elif format == 'yaml':
        resource_val = yaml.load(open(filename, 'rb'))
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


