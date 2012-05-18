# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import types

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
    im_class = lambda meth: meth.__self__.__class__
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    im_class = lambda meth: meth.im_class

try:
    from itertools import imap, izip
except ImportError: # python 3
    imap = map
    izip = zip

if PY3:
    import html.entities as htmlentitydefs
else:
    import htmlentitydefs

