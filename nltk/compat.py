# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import types

# Python 2/3 compatibility layer. Based on six.

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
    im_class = lambda meth: meth.__self__.__class__
    xrange = range
    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"

    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    im_class = lambda meth: meth.im_class
    xrange = xrange
    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"

    try:
        from cStringIO import StringIO
    except:
        from StringIO import StringIO
    BytesIO = StringIO
try:
    from itertools import imap, izip
except ImportError: # python 3
    imap = map
    izip = zip

def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return getattr(d, _iterkeys)()

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return getattr(d, _itervalues)()

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return getattr(d, _iteritems)()

if PY3:
    import html.entities as htmlentitydefs
else:
    import htmlentitydefs

