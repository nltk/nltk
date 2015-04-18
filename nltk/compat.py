# -*- coding: utf-8 -*-
# Natural Language Toolkit: Compatibility
#
# Copyright (C) 2001-2015 NLTK Project
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import absolute_import, print_function
import sys
import types
from functools import wraps

# Python 2/3 compatibility layer. Based on six.

PY3 = sys.version_info[0] == 3
PY26 = sys.version_info[:2] == (2, 6)

if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s

    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
    get_im_class = lambda meth: meth.__self__.__class__
    xrange = range
    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    from imp import reload
    raw_input = input

    imap = map
    izip = zip

    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO

    import html.entities as htmlentitydefs
    from urllib.request import (urlopen, ProxyHandler, build_opener,
        install_opener, getproxies, HTTPPasswordMgrWithDefaultRealm,
        ProxyBasicAuthHandler, ProxyDigestAuthHandler, Request,
        url2pathname)
    from urllib.error import HTTPError, URLError
    from urllib.parse import quote_plus, unquote_plus, urlencode

    from collections import Counter

else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")

    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    get_im_class = lambda meth: meth.im_class
    xrange = xrange
    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    reload = reload
    raw_input = raw_input

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
        ProxyDigestAuthHandler, Request)
    from urllib import getproxies, quote_plus, unquote_plus, urlencode, url2pathname

    # Maps py2 tkinter package structure to py3 using import hook (PEP 302)
    class TkinterPackage(object):
        def __init__(self):
            self.mod = __import__("Tkinter")
            self.__path__ = ["nltk_py2_tkinter_package_path"]
        def __getattr__(self, name):
            return getattr(self.mod, name)

    class TkinterLoader(object):
        def __init__(self):
            # module name mapping from py3 to py2
            self.module_map = {
                "tkinter": "Tkinter",
                "tkinter.filedialog": "tkFileDialog",
                "tkinter.font": "tkFont",
                "tkinter.messagebox": "tkMessageBox",
            }
        def find_module(self, name, path=None):
            # we are only interested in tkinter modules listed
            # in self.module_map
            if name in self.module_map:
                return self
        def load_module(self, name):
            if name not in sys.modules:
                if name == 'tkinter':
                    mod = TkinterPackage()
                else:
                    mod = __import__(self.module_map[name])
                sys.modules[name] = mod
            return sys.modules[name]

    sys.meta_path.insert(0, TkinterLoader())

    if PY26:
        from operator import itemgetter
        from heapq import nlargest
        from itertools import repeat, ifilter

        class Counter(dict):
            '''Dict subclass for counting hashable objects.  Sometimes called a bag
            or multiset.  Elements are stored as dictionary keys and their counts
            are stored as dictionary values.

            >>> Counter('zyzygy')
            Counter({'y': 3, 'z': 2, 'g': 1})

            '''

            def __init__(self, iterable=None, **kwds):
                '''Create a new, empty Counter object.  And if given, count elements
                from an input iterable.  Or, initialize the count from another mapping
                of elements to their counts.

                >>> Counter()                           # a new, empty counter
                >>> Counter('gallahad')                 # a new counter from an iterable
                >>> Counter({'a': 4, 'b': 2})           # a new counter from a mapping
                >>> Counter(a=4, b=2)                   # a new counter from keyword args

                '''
                self.update(iterable, **kwds)

            def __missing__(self, key):
                return 0

            def most_common(self, n=None):
                '''List the n most common elements and their counts from the most
                common to the least.  If n is None, then list all element counts.

                >>> Counter('abracadabra').most_common(3)
                [('a', 5), ('r', 2), ('b', 2)]

                '''
                if n is None:
                    return sorted(self.iteritems(), key=itemgetter(1), reverse=True)
                return nlargest(n, self.iteritems(), key=itemgetter(1))

            def elements(self):
                '''Iterator over elements repeating each as many times as its count.

                >>> c = Counter('ABCABC')
                >>> sorted(c.elements())
                ['A', 'A', 'B', 'B', 'C', 'C']

                If an element's count has been set to zero or is a negative number,
                elements() will ignore it.

                '''
                for elem, count in self.iteritems():
                    for _ in repeat(None, count):
                        yield elem

            # Override dict methods where the meaning changes for Counter objects.

            @classmethod
            def fromkeys(cls, iterable, v=None):
                raise NotImplementedError(
                    'Counter.fromkeys() is undefined.  Use Counter(iterable) instead.')

            def update(self, iterable=None, **kwds):
                '''Like dict.update() but add counts instead of replacing them.

                Source can be an iterable, a dictionary, or another Counter instance.

                >>> c = Counter('which')
                >>> c.update('witch')           # add elements from another iterable
                >>> d = Counter('watch')
                >>> c.update(d)                 # add elements from another counter
                >>> c['h']                      # four 'h' in which, witch, and watch
                4

                '''
                if iterable is not None:
                    if hasattr(iterable, 'iteritems'):
                        if self:
                            self_get = self.get
                            for elem, count in iterable.iteritems():
                                self[elem] = self_get(elem, 0) + count
                        else:
                            dict.update(self, iterable) # fast path when counter is empty
                    else:
                        self_get = self.get
                        for elem in iterable:
                            self[elem] = self_get(elem, 0) + 1
                if kwds:
                    self.update(kwds)

            def copy(self):
                'Like dict.copy() but returns a Counter instance instead of a dict.'
                return Counter(self)

            def __delitem__(self, elem):
                'Like dict.__delitem__() but does not raise KeyError for missing values.'
                if elem in self:
                    dict.__delitem__(self, elem)

            def __repr__(self):
                if not self:
                    return '%s()' % self.__class__.__name__
                items = ', '.join(map('%r: %r'.__mod__, self.most_common()))
                return '%s({%s})' % (self.__class__.__name__, items)

            # Multiset-style mathematical operations discussed in:
            #       Knuth TAOCP Volume II section 4.6.3 exercise 19
            #       and at http://en.wikipedia.org/wiki/Multiset
            #
            # Outputs guaranteed to only include positive counts.
            #
            # To strip negative and zero counts, add-in an empty counter:
            #       c += Counter()

            def __add__(self, other):
                '''Add counts from two counters.

                >>> Counter('abbb') + Counter('bcc')
                Counter({'b': 4, 'c': 2, 'a': 1})


                '''
                if not isinstance(other, Counter):
                    return NotImplemented
                result = Counter()
                for elem in set(self) | set(other):
                    newcount = self[elem] + other[elem]
                    if newcount > 0:
                        result[elem] = newcount
                return result

            def __sub__(self, other):
                ''' Subtract count, but keep only results with positive counts.

                >>> Counter('abbbc') - Counter('bccd')
                Counter({'b': 2, 'a': 1})

                '''
                if not isinstance(other, Counter):
                    return NotImplemented
                result = Counter()
                for elem in set(self) | set(other):
                    newcount = self[elem] - other[elem]
                    if newcount > 0:
                        result[elem] = newcount
                return result

            def __or__(self, other):
                '''Union is the maximum of value in either of the input counters.

                >>> Counter('abbb') | Counter('bcc')
                Counter({'b': 3, 'c': 2, 'a': 1})

                '''
                if not isinstance(other, Counter):
                    return NotImplemented
                _max = max
                result = Counter()
                for elem in set(self) | set(other):
                    newcount = _max(self[elem], other[elem])
                    if newcount > 0:
                        result[elem] = newcount
                return result

            def __and__(self, other):
                ''' Intersection is the minimum of corresponding counts.

                >>> Counter('abbb') & Counter('bcc')
                Counter({'b': 1})

                '''
                if not isinstance(other, Counter):
                    return NotImplemented
                _min = min
                result = Counter()
                if len(self) < len(other):
                    self, other = other, self
                for elem in ifilter(self.__contains__, other):
                    newcount = _min(self[elem], other[elem])
                    if newcount > 0:
                        result[elem] = newcount
                return result

    else:
        from collections import Counter


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return getattr(d, _iterkeys)()

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return getattr(d, _itervalues)()

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return getattr(d, _iteritems)()

try:
    from functools import total_ordering
except ImportError: # python 2.6
    def total_ordering(cls):
        """Class decorator that fills in missing ordering methods"""
        convert = {
            '__lt__': [('__gt__', lambda self, other: not (self < other or self == other)),
                       ('__le__', lambda self, other: self < other or self == other),
                       ('__ge__', lambda self, other: not self < other)],
            '__le__': [('__ge__', lambda self, other: not self <= other or self == other),
                       ('__lt__', lambda self, other: self <= other and not self == other),
                       ('__gt__', lambda self, other: not self <= other)],
            '__gt__': [('__lt__', lambda self, other: not (self > other or self == other)),
                       ('__ge__', lambda self, other: self > other or self == other),
                       ('__le__', lambda self, other: not self > other)],
            '__ge__': [('__le__', lambda self, other: (not self >= other) or self == other),
                       ('__gt__', lambda self, other: self >= other and not self == other),
                       ('__lt__', lambda self, other: not self >= other)]
        }
        roots = set(dir(cls)) & set(convert)
        if not roots:
            raise ValueError('must define at least one ordering operation: < > <= >=')
        root = max(roots)       # prefer __lt__ to __le__ to __gt__ to __ge__
        for opname, opfunc in convert[root]:
            if opname not in roots:
                opfunc.__name__ = opname
                opfunc.__doc__ = getattr(int, opname).__doc__
                setattr(cls, opname, opfunc)
        return cls


# ======= Compatibility for datasets that care about Python versions ========

# The following datasets have a /PY3 subdirectory containing
# a full copy of the data which has been re-encoded or repickled.

_PY3_DATA_UPDATES = []

if sys.platform.startswith('win'):
    _PY3_DATA_UPDATES = ["chunkers\maxent_ne_chunker",
                         "help\tagsets",
                         "taggers\maxent_treebank_pos_tagger",
                         "tokenizers\punkt"]
else:
    _PY3_DATA_UPDATES = ["chunkers/maxent_ne_chunker",
                        "help/tagsets",
                        "taggers/maxent_treebank_pos_tagger",
                        "tokenizers/punkt"]

def add_py3_data(path):
    if PY3:
        for item in _PY3_DATA_UPDATES:
            if item in str(path) and "/PY3" not in str(path):
                pos = path.index(item) + len(item)
                if path[pos:pos+4] == ".zip":
                    pos += 4
                path = path[:pos] + "/PY3" + path[pos:]
                break
    return path

# for use in adding /PY3 to the second (filename) argument
# of the file pointers in data.py
def py3_data(init_func):
    def _decorator(*args, **kwargs):
        args = (args[0], add_py3_data(args[1])) + args[2:]
        return init_func(*args, **kwargs)
    return wraps(init_func)(_decorator)

# ======= Compatibility layer for __str__ and __repr__ ==========

import unicodedata
import functools

def remove_accents(text):

    if isinstance(text, bytes):
        text = text.decode('ascii')

    category = unicodedata.category  # this gives a small (~10%) speedup
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text) if category(c) != 'Mn'
    )

# Select the best transliteration method:
try:
    # Older versions of Unidecode are licensed under Artistic License;
    # assume an older version is installed.
    from unidecode import unidecode as transliterate
except ImportError:
    try:
        # text-unidecode implementation is worse than Unidecode
        # implementation so Unidecode is preferred.
        from text_unidecode import unidecode as transliterate
    except ImportError:
        # This transliteration method should be enough
        # for many Western languages.
        transliterate = remove_accents


def python_2_unicode_compatible(klass):
    """
    This decorator defines __unicode__ method and fixes
    __repr__ and __str__ methods under Python 2.

    To support Python 2 and 3 with a single code base,
    define __str__ and __repr__ methods returning unicode
    text and apply this decorator to the class.

    Original __repr__ and __str__ would be available
    as unicode_repr and __unicode__ (under both Python 2
    and Python 3).
    """

    if not issubclass(klass, object):
        raise ValueError("This decorator doesn't work for old-style classes")

    # both __unicode__ and unicode_repr are public because they
    # may be useful in console under Python 2.x

    # if __str__ or __repr__ are not overriden in a subclass,
    # they may be already fixed by this decorator in a parent class
    # and we shouldn't them again

    if not _was_fixed(klass.__str__):
        klass.__unicode__ = klass.__str__
        if not PY3:
            klass.__str__ = _7bit(_transliterated(klass.__unicode__))


    if not _was_fixed(klass.__repr__):
        klass.unicode_repr = klass.__repr__
        if not PY3:
            klass.__repr__ = _7bit(klass.unicode_repr)

    return klass


def unicode_repr(obj):
    """
    For classes that was fixed with @python_2_unicode_compatible
    ``unicode_repr`` returns ``obj.unicode_repr()``; for unicode strings
    the result is returned without "u" letter (to make output the
    same under Python 2.x and Python 3.x); for other variables
    it is the same as ``repr``.
    """
    if PY3:
        return repr(obj)

    # Python 2.x
    if hasattr(obj, 'unicode_repr'):
        return obj.unicode_repr()

    if isinstance(obj, unicode):
        return repr(obj)[1:]  # strip "u" letter from output

    return repr(obj)


def _transliterated(method):
    def wrapper(self):
        return transliterate(method(self))

    functools.update_wrapper(wrapper, method, ["__name__", "__doc__"])
    if hasattr(method, "_nltk_compat_7bit"):
        wrapper._nltk_compat_7bit = method._nltk_compat_7bit

    wrapper._nltk_compat_transliterated = True
    return wrapper


def _7bit(method):
    def wrapper(self):
        return method(self).encode('ascii', 'backslashreplace')

    functools.update_wrapper(wrapper, method, ["__name__", "__doc__"])

    if hasattr(method, "_nltk_compat_transliterated"):
        wrapper._nltk_compat_transliterated = method._nltk_compat_transliterated

    wrapper._nltk_compat_7bit = True
    return wrapper


def _was_fixed(method):
    return (getattr(method, "_nltk_compat_7bit", False) or
            getattr(method, "_nltk_compat_transliterated", False))
