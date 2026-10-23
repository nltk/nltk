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

import six
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


# Python 3's OSError subclasses, for 2.7: our own code raises these; a
# stdlib error on 2.7 is a plain EnvironmentError, so catch sites that must
# recognise one from the stdlib test ``is_errno`` instead of the class.
import errno as _errno

if six.PY3:
    from builtins import (  # noqa: F401
        FileNotFoundError,
        PermissionError,
        IsADirectoryError,
        NotADirectoryError,
        FileExistsError,
        TimeoutError,
        ChildProcessError,
        ProcessLookupError,
        BrokenPipeError,
        ConnectionError,
        InterruptedError,
    )
    from types import SimpleNamespace  # noqa: F401
else:

    class _CompatOSError(EnvironmentError):
        _errno = None

        def __init__(self, *args):
            EnvironmentError.__init__(self, *args)
            if self.errno is None and self._errno is not None and len(args) < 2:
                self.errno = self._errno
                if len(args) == 1:
                    self.strerror = args[0]

    class FileNotFoundError(_CompatOSError):
        _errno = _errno.ENOENT

    class PermissionError(_CompatOSError):
        _errno = _errno.EACCES

    class IsADirectoryError(_CompatOSError):
        _errno = _errno.EISDIR

    class NotADirectoryError(_CompatOSError):
        _errno = _errno.ENOTDIR

    class FileExistsError(_CompatOSError):
        _errno = _errno.EEXIST

    class TimeoutError(_CompatOSError):
        _errno = _errno.ETIMEDOUT

    class ChildProcessError(_CompatOSError):
        _errno = _errno.ECHILD

    class ProcessLookupError(_CompatOSError):
        _errno = _errno.ESRCH

    class BrokenPipeError(_CompatOSError):
        _errno = _errno.EPIPE

    class ConnectionError(_CompatOSError):
        pass

    class InterruptedError(_CompatOSError):
        _errno = _errno.EINTR

    class SimpleNamespace(object):
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def __repr__(self):
            items = ", ".join("%s=%r" % kv for kv in sorted(self.__dict__.items()))
            return "namespace(%s)" % items

        def __eq__(self, other):
            return isinstance(other, SimpleNamespace) and self.__dict__ == other.__dict__

        def __ne__(self, other):
            return not self == other


if six.PY3:
    from os import PathLike, fspath  # noqa: F401
else:

    class PathLike(object):
        """``os.PathLike`` for 2.7: an object naming a path through ``__fspath__``."""

        def __fspath__(self):
            raise NotImplementedError

        @classmethod
        def __subclasshook__(cls, subclass):
            if cls is PathLike:
                return hasattr(subclass, "__fspath__")
            return NotImplemented

    def fspath(path):
        """``os.fspath`` for 2.7: text or bytes pass through, a ``__fspath__``
        object is asked, anything else is refused (never coerced with str)."""
        if isinstance(path, (six.text_type, bytes)):
            return path
        fs = getattr(type(path), "__fspath__", None)
        if fs is None:
            raise TypeError(
                "expected str, bytes or os.PathLike object, not %s" % type(path).__name__
            )
        result = fs(path)
        if isinstance(result, (six.text_type, bytes)):
            return result
        raise TypeError(
            "expected %s.__fspath__() to return str or bytes, not %s"
            % (type(path).__name__, type(result).__name__)
        )


def load_module_from_file(name, path):
    """Import the source file at *path* as module *name* on 2.7 and 3."""
    if six.PY3:
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    import imp

    return imp.load_source(name, path)


import time as _time

#: CPU time of the process: ``time.process_time`` (3.3+), ``time.clock`` on 2.7.
process_time = getattr(_time, "process_time", None) or _time.clock
#: Wall clock for intervals: ``time.perf_counter`` (3.3+), ``time.time`` on 2.7.
perf_counter = getattr(_time, "perf_counter", None) or _time.time


if six.PY3:
    from os import fsdecode, fsencode  # noqa: F401
else:
    import sys as _sys

    def fsdecode(value):
        """``os.fsdecode`` for 2.7: bytes to text with the filesystem encoding."""
        if isinstance(value, six.text_type):
            return value
        return value.decode(_sys.getfilesystemencoding() or "utf-8", "strict")

    def fsencode(value):
        """``os.fsencode`` for 2.7: text to bytes with the filesystem encoding."""
        if isinstance(value, bytes):
            return value
        return value.encode(_sys.getfilesystemencoding() or "utf-8", "strict")


try:
    from subprocess import TimeoutExpired  # noqa: F401
except ImportError:  # Python 2.7: the subprocess32 backport carries it
    try:
        from subprocess32 import TimeoutExpired  # noqa: F401
    except ImportError:

        class TimeoutExpired(Exception):
            """``subprocess.TimeoutExpired`` stand-in without the backport."""


_ERRNO_CLASSES = {
    _errno.ENOENT: FileNotFoundError,
    _errno.EACCES: PermissionError,
    _errno.EPERM: PermissionError,
    _errno.EISDIR: IsADirectoryError,
    _errno.ENOTDIR: NotADirectoryError,
    _errno.EEXIST: FileExistsError,
    _errno.EINTR: InterruptedError,
}


def is_errno(exc, *codes):
    """True when *exc* is an environment error carrying one of *codes*, or an
    instance of the Python 3 class that code maps to (both interpreters)."""
    if not isinstance(exc, EnvironmentError):
        return False
    if getattr(exc, "errno", None) in codes:
        return True
    return any(isinstance(exc, _ERRNO_CLASSES[c]) for c in codes if c in _ERRNO_CLASSES)


def keyword_only(positional):
    """Refuse positional arguments beyond ``positional``: Python 2 has no
    bare ``*`` separator, so the security helpers keep their keyword-only
    parameters keyword-only through this guard."""

    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if len(args) > positional:
                raise TypeError(
                    "%s() takes at most %d positional argument%s (%d given)"
                    % (fn.__name__, positional, "" if positional == 1 else "s", len(args))
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorate


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
