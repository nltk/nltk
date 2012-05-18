# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import types

# Python 2/3 compatibility layer. Based on six.

PY3 = sys.version_info[0] == 3

if PY3:
    def u(s):
        return s

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

    imap = map
    izip = zip

    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO

    import html.entities as htmlentitydefs
    from urllib.request import (urlopen, ProxyHandler, build_opener,
        install_opener, getproxies, HTTPPasswordMgrWithDefaultRealm,
        ProxyBasicAuthHandler, ProxyDigestAuthHandler)
    from urllib.error import HTTPError, URLError
    from urllib.parse import quote_plus, unquote_plus, urlencode

else:
    def u(s):
        return unicode(s, "unicode_escape")

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

    from itertools import imap, izip

    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    BytesIO = StringIO

    import htmlentitydefs
    from urllib2 import (urlopen, HTTPError, URLError,
        ProxyHandler, build_opener, install_opener,
        HTTPPasswordMgrWithDefaultRealm, ProxyBasicAuthHandler,
        ProxyDigestAuthHandler)
    from urllib import getproxies, quote_plus, unquote_plus, urlencode

def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return getattr(d, _iterkeys)()

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return getattr(d, _itervalues)()

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return getattr(d, _iteritems)()

