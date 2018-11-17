# -*- coding: utf-8 -*-
# Natural Language Toolkit: Compatibility
#
# Copyright (C) 2001-2019 NLTK Project
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import absolute_import, print_function
import os
import sys
from functools import update_wrapper, wraps
import fractions
import unicodedata

from six import string_types, text_type

# Python 2/3 compatibility layer. Based on six.

PY3 = sys.version_info[0] == 3

if PY3:

    def get_im_class(meth):
        return meth.__self__.__class__

    import io

    StringIO = io.StringIO
    BytesIO = io.BytesIO

    from datetime import timezone

    UTC = timezone.utc

    from tempfile import TemporaryDirectory

else:

    def get_im_class(meth):
        return meth.im_class

    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    BytesIO = StringIO

    from datetime import tzinfo, timedelta

    ZERO = timedelta(0)
    HOUR = timedelta(hours=1)

    # A UTC class for python 2.7
    class UTC(tzinfo):
        """UTC"""

        def utcoffset(self, dt):
            return ZERO

        def tzname(self, dt):
            return "UTC"

        def dst(self, dt):
            return ZERO

    UTC = UTC()

    import csv
    import codecs
    import cStringIO

    class UnicodeWriter:
        """
        A CSV writer which will write rows to CSV file "f",
        which is encoded in the given encoding.
        see https://docs.python.org/2/library/csv.html
        """

        def __init__(
            self, f, dialect=csv.excel, encoding="utf-8", errors='replace', **kwds
        ):
            # Redirect output to a queue
            self.queue = cStringIO.StringIO()
            self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
            self.stream = f
            encoder_cls = codecs.getincrementalencoder(encoding)
            self.encoder = encoder_cls(errors=errors)

        def encode(self, data):
            if isinstance(data, string_types):
                return data.encode("utf-8")
            else:
                return data

        def writerow(self, row):
            self.writer.writerow([self.encode(s) for s in row])
            # Fetch UTF-8 output from the queue ...
            data = self.queue.getvalue()
            data = data.decode("utf-8")
            # ... and reencode it into the target encoding
            data = self.encoder.encode(data, 'replace')
            # write to the target stream
            self.stream.write(data)
            # empty queue
            self.queue.truncate(0)

    import warnings as _warnings
    import os as _os
    from tempfile import mkdtemp

    class TemporaryDirectory(object):
        """Create and return a temporary directory.  This has the same
        behavior as mkdtemp but can be used as a context manager.  For
        example:

            with TemporaryDirectory() as tmpdir:
                ...

        Upon exiting the context, the directory and everything contained
        in it are removed.

        http://stackoverflow.com/questions/19296146/tempfile-temporarydirectory-context-manager-in-python-2-7
        """

        def __init__(self, suffix="", prefix="tmp", dir=None):
            self._closed = False
            self.name = None  # Handle mkdtemp raising an exception
            self.name = mkdtemp(suffix, prefix, dir)

        def __repr__(self):
            return "<{} {!r}>".format(self.__class__.__name__, self.name)

        def __enter__(self):
            return self.name

        def cleanup(self, _warn=False):
            if self.name and not self._closed:
                try:
                    self._rmtree(self.name)
                except (TypeError, AttributeError) as ex:
                    # Issue #10188: Emit a warning on stderr
                    # if the directory could not be cleaned
                    # up due to missing globals
                    if "None" not in str(ex):
                        raise
                    print(
                        "ERROR: {!r} while cleaning up {!r}".format(ex, self),
                        file=sys.stderr,
                    )
                    return
                self._closed = True
                if _warn:
                    self._warn("Implicitly cleaning up {!r}".format(self), Warning)

        def __exit__(self, exc, value, tb):
            self.cleanup()

        def __del__(self):
            # Issue a Warning if implicit cleanup needed
            self.cleanup(_warn=True)

        # XXX (ncoghlan): The following code attempts to make
        # this class tolerant of the module nulling out process
        # that happens during CPython interpreter shutdown
        # Alas, it doesn't actually manage it. See issue #10188
        _listdir = staticmethod(_os.listdir)
        _path_join = staticmethod(_os.path.join)
        _isdir = staticmethod(_os.path.isdir)
        _islink = staticmethod(_os.path.islink)
        _remove = staticmethod(_os.remove)
        _rmdir = staticmethod(_os.rmdir)
        _warn = _warnings.warn

        def _rmtree(self, path):
            # Essentially a stripped down version of shutil.rmtree.  We can't
            # use globals because they may be None'ed out at shutdown.
            for name in self._listdir(path):
                fullname = self._path_join(path, name)
                try:
                    isdir = self._isdir(fullname) and not self._islink(fullname)
                except OSError:
                    isdir = False
                if isdir:
                    self._rmtree(fullname)
                else:
                    try:
                        self._remove(fullname)
                    except OSError:
                        pass
            try:
                self._rmdir(path)
            except OSError:
                pass


# ======= Compatibility for datasets that care about Python versions ========

# The following datasets have a /PY3 subdirectory containing
# a full copy of the data which has been re-encoded or repickled.
DATA_UPDATES = [
    ("chunkers", "maxent_ne_chunker"),
    ("help", "tagsets"),
    ("taggers", "maxent_treebank_pos_tagger"),
    ("tokenizers", "punkt"),
]

_PY3_DATA_UPDATES = [os.path.join(*path_list) for path_list in DATA_UPDATES]


def add_py3_data(path):
    if PY3:
        for item in _PY3_DATA_UPDATES:
            if item in str(path) and "/PY3" not in str(path):
                pos = path.index(item) + len(item)
                if path[pos : pos + 4] == ".zip":
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

    if isinstance(obj, text_type):
        return repr(obj)[1:]  # strip "u" letter from output

    return repr(obj)


def _transliterated(method):
    def wrapper(self):
        return transliterate(method(self))

    update_wrapper(wrapper, method, ["__name__", "__doc__"])
    if hasattr(method, "_nltk_compat_7bit"):
        wrapper._nltk_compat_7bit = method._nltk_compat_7bit

    wrapper._nltk_compat_transliterated = True
    return wrapper


def _7bit(method):
    def wrapper(self):
        return method(self).encode('ascii', 'backslashreplace')

    update_wrapper(wrapper, method, ["__name__", "__doc__"])

    if hasattr(method, "_nltk_compat_transliterated"):
        wrapper._nltk_compat_transliterated = method._nltk_compat_transliterated

    wrapper._nltk_compat_7bit = True
    return wrapper


def _was_fixed(method):
    return getattr(method, "_nltk_compat_7bit", False) or getattr(
        method, "_nltk_compat_transliterated", False
    )


class Fraction(fractions.Fraction):
    """
    This is a simplified backwards compatible version of fractions.Fraction
    from Python >=3.5. It adds the `_normalize` parameter such that it does
    not normalize the denominator to the Greatest Common Divisor (gcd) when
    the numerator is 0.

    This is most probably only used by the nltk.translate.bleu_score.py where
    numerator and denominator of the different ngram precisions are mutable.
    But the idea of "mutable" fraction might not be applicable to other usages,
    See http://stackoverflow.com/questions/34561265

    This objects should be deprecated once NLTK stops supporting Python < 3.5
    See https://github.com/nltk/nltk/issues/1330
    """

    def __new__(cls, numerator=0, denominator=None, _normalize=True):
        cls = super(Fraction, cls).__new__(cls, numerator, denominator)
        # To emulate fraction.Fraction.from_float across Python >=2.7,
        # check that numerator is an integer and denominator is not None.
        if not _normalize and type(numerator) == int and denominator:
            cls._numerator = numerator
            cls._denominator = denominator
        return cls
