# -*- coding: utf-8 -*-
# Natural Language Toolkit: security helpers for the 3.4 maintenance line
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
Small, dependency-free helpers behind the security fixes of this
maintenance line. Each one closes one class of vulnerability that the 3.10
line closed with its guard framework; here the fix is applied in place at
the sink, so the helpers stay deliberately minimal.

* :func:`restricted_pickle_load`: unpickle only the classes NLTK's own
  pickled resources need (CWE-502).
* :func:`contained_path`: a path joined from caller input must stay inside
  its root once links are resolved (CWE-22, CWE-59).
* :func:`check_zip_member`: an archive member name must not escape the
  extraction root (Zip-Slip, CWE-22) nor another package's directory.
* :func:`check_url_scheme`: only http and https may be fetched (CWE-918).
* :func:`decode_string_literal`: a quoted literal is decoded, never
  evaluated (CWE-94).
* :func:`check_java_options`: JVM flags come from an allowlist (CWE-88).
* :func:`untrusted_executable_reason`: a tool binary must sit on a path no
  other account can write (CWE-426).
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import errno
import io
import os
import pickle
import re
import stat
import sys

from six import PY2, binary_type, string_types, text_type
from six.moves.urllib.parse import urlsplit

__all__ = [
    "RestrictedUnpickler",
    "restricted_pickle_load",
    "restricted_pickle_loads",
    "contained_path",
    "check_zip_member",
    "check_url_scheme",
    "decode_string_literal",
    "check_java_options",
    "untrusted_executable_reason",
    "MAX_RESOURCE_BYTES",
]


class SecurityError(ValueError):
    """Raised when an input would cross one of the boundaries kept here."""


# ----------------------------------------------------------------------
# Deserialisation (CWE-502)
# ----------------------------------------------------------------------

#: Modules whose classes a pickled NLTK resource may legitimately reference.
#: Everything else (``os``, ``subprocess``, ``builtins.eval``, ...) is refused
#: before any object is built, so a planted pickle cannot run code.
_PICKLE_MODULE_PREFIXES = ("nltk.",)
_PICKLE_ALLOWED = {
    "builtins": {"set", "frozenset", "list", "dict", "tuple", "bytes", "str",
                 "int", "float", "bool", "complex", "object", "slice", "range",
                 "bytearray"},
    "__builtin__": {"set", "frozenset", "list", "dict", "tuple", "str", "unicode",
                    "int", "long", "float", "bool", "complex", "object", "slice",
                    "xrange", "bytearray"},
    "collections": {"OrderedDict", "defaultdict", "Counter", "deque"},
    "copy_reg": {"_reconstructor"},
    "copyreg": {"_reconstructor"},
    "_codecs": {"encode"},
    "numpy": {"ndarray", "dtype", "float64", "float32", "int64", "int32", "bool_"},
    "numpy.core.multiarray": {"_reconstruct", "scalar"},
    "numpy._core.multiarray": {"_reconstruct", "scalar"},
    "scipy.sparse.csr": {"csr_matrix"},
    "scipy.sparse._csr": {"csr_matrix"},
    "sklearn.svm.classes": {"SVC"},
    "sklearn.svm._classes": {"SVC"},
}

_Unpickler = pickle.Unpickler if PY2 else pickle._Unpickler


class RestrictedUnpickler(_Unpickler):
    """An unpickler that refuses every global outside the allowlist.

    NLTK's own pickled models reference NLTK classes and a few containers;
    ``find_class`` is the single point every pickle opcode that names a
    global goes through, so refusing there stops ``os.system`` or any other
    callable from ever being looked up (CWE-502).
    """

    def find_class(self, module, name):
        if module.startswith(_PICKLE_MODULE_PREFIXES) and not name.startswith("_"):
            return _Unpickler.find_class(self, module, name)
        allowed = _PICKLE_ALLOWED.get(module)
        if allowed is not None and name in allowed:
            return _Unpickler.find_class(self, module, name)
        raise pickle.UnpicklingError(
            "refusing to unpickle %s.%s: not an NLTK resource class" % (module, name)
        )

    if PY2:
        # The pure-Python 2.7 Unpickler resolves ``c<module>\n<name>`` through
        # find_class as well; the ``obj``/``inst`` opcodes call it too.
        pass


def restricted_pickle_load(fileobj):
    """Load a pickle from *fileobj* with :class:`RestrictedUnpickler`."""
    return RestrictedUnpickler(fileobj).load()


def restricted_pickle_loads(data):
    """Load a pickle from the bytes *data* with :class:`RestrictedUnpickler`."""
    return RestrictedUnpickler(io.BytesIO(data)).load()


#: Upper bound on one loaded resource (a pickle, a YAML or JSON document): a
#: resource past this is refused before the decoder sees it (CWE-400).
MAX_RESOURCE_BYTES = 1024 * 1024 * 1024


def read_bounded(fileobj, limit=MAX_RESOURCE_BYTES, what="resource"):
    """Read *fileobj* to the end, refusing a body longer than *limit*."""
    data = fileobj.read(limit + 1)
    if len(data) > limit:
        raise SecurityError("%s exceeds %d bytes" % (what, limit))
    return data


# ----------------------------------------------------------------------
# Paths (CWE-22, CWE-59)
# ----------------------------------------------------------------------


def _realpath(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def contained_path(root, path, what="path"):
    """Return *path* when it lies inside *root* once every link is resolved.

    Both arguments are filesystem paths; the check compares real paths, so a
    ``..`` component, an absolute *path*, or a symbolic link pointing outside
    *root* are all refused with :class:`SecurityError` (CWE-22, CWE-59).
    """
    real_root = _realpath(root)
    real_path = _realpath(path)
    if real_path == real_root or real_path.startswith(real_root.rstrip(os.sep) + os.sep):
        return path
    raise SecurityError(
        "%s %r escapes its root %r" % (what, path, root)
    )


def has_parent_reference(name):
    """True when a slash- or backslash-separated *name* steps upward."""
    return any(part == ".." for part in re.split(r"[\\/]+", name))


# ----------------------------------------------------------------------
# Archives (CWE-22)
# ----------------------------------------------------------------------

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def check_zip_member(name, root, expected_root=None):
    """Refuse an archive member that would write outside *root*.

    A member is refused when its name is absolute, carries a drive letter, a
    NUL byte or a ``..`` component, when its first path component is not
    *expected_root* (the owning package's directory) if one is given, or when
    any existing directory on its target path is a symbolic link (a planted
    link would redirect the write; CWE-22, CWE-59). Returns the target path.
    """
    if "\x00" in name:
        raise SecurityError("archive member name holds a NUL byte: %r" % name)
    if name.startswith(("/", "\\")) or _WINDOWS_DRIVE_RE.match(name):
        raise SecurityError("archive member is an absolute path: %r" % name)
    if has_parent_reference(name):
        raise SecurityError("archive member steps outside the root: %r" % name)
    parts = [p for p in re.split(r"[\\/]+", name) if p and p != "."]
    if not parts:
        raise SecurityError("archive member has an empty name: %r" % name)
    if expected_root is not None and parts[0] != expected_root:
        raise SecurityError(
            "archive member %r does not belong to package %r" % (name, expected_root)
        )
    target = os.path.join(root, *parts)
    contained_path(root, target, "archive member %r" % name)
    probe = root
    for part in parts[:-1]:
        probe = os.path.join(probe, part)
        if os.path.islink(probe):
            raise SecurityError(
                "archive member %r would write through the link %r" % (name, probe)
            )
    return target


# ----------------------------------------------------------------------
# Network (CWE-918)
# ----------------------------------------------------------------------

_ALLOWED_SCHEMES = ("http", "https")


def check_url_scheme(url, what="URL"):
    """Return *url* when its scheme is http or https; refuse file, ftp, data
    and every other scheme a redirect or an index could smuggle (CWE-918)."""
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise SecurityError("%s %r: only http and https may be fetched" % (what, url))
    return url


# ----------------------------------------------------------------------
# Literals (CWE-94)
# ----------------------------------------------------------------------

_ESCAPE_RE = re.compile(
    r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|[0-7]{1,3}|N\{[^}]*\}|.)",
    re.DOTALL,
)


def decode_string_literal(literal):
    """Decode a quoted Python string literal without ``eval``.

    Accepts the forms the NLTK readers write (optional ``u``/``b``/``r``
    prefix, single or double quotes) and resolves the usual escapes; any
    other content raises :class:`ValueError` (CWE-94).
    """
    text = literal
    prefix = ""
    while text and text[0] in "uUbBrR":
        prefix += text[0].lower()
        text = text[1:]
    if len(text) < 2 or text[0] not in "'\"" or text[-1] != text[0]:
        raise ValueError("not a quoted string literal: %r" % literal)
    body = text[1:-1]
    if "r" in prefix:
        return body
    if "b" in prefix:
        return codecs.escape_decode(body.encode("latin-1"))[0] if not PY2 else codecs.escape_decode(body.encode("latin-1"))[0]
    return codecs.decode(body, "unicode_escape")


# ----------------------------------------------------------------------
# JVM options (CWE-88)
# ----------------------------------------------------------------------

#: Exactly the flag shapes NLTK's Java wrappers and the Stanford
#: documentation use. A denylist cannot keep up with ``-jar``, ``@argfile``
#: or ``-XX:OnError=<cmd>``; everything else is refused.
_JAVA_OPTION_RE = re.compile(
    r"^(?:-(?:Xmx|Xms|Xss|mx|ms|ss)\d+[kKmMgG]?|-verbose(?::[a-z]+)?|-server|-client"
    r"|-ea|-da|--add-modules=[A-Za-z0-9_.,]+|-Dfile\.encoding=[A-Za-z0-9_-]+"
    r"|-Duser\.(?:language|country|timezone)=[A-Za-z0-9_/+-]+)$"
)


def check_java_options(options):
    """Return *options* when every flag matches the allowlist (CWE-88)."""
    for flag in options:
        if not isinstance(flag, string_types) or not _JAVA_OPTION_RE.match(flag):
            raise ValueError(
                "java option %r is not in the allowlist of JVM flags NLTK passes"
                % (flag,)
            )
    return list(options)


# ----------------------------------------------------------------------
# Executables (CWE-426)
# ----------------------------------------------------------------------


def untrusted_executable_reason(path):
    """Why *path* is not a trustworthy binary to execute, or None.

    The binary and every directory above it must be owned by this account
    or root and be writable by nobody else; a relative path is refused too,
    since it would resolve against the current directory (CWE-426).
    """
    if not os.path.isabs(path):
        return "the path is relative and would resolve against the current directory"
    real = os.path.realpath(path)
    if not os.path.isfile(real):
        return "not a regular file"
    if os.name != "posix":
        return None
    uid = os.geteuid()
    probe = real
    while True:
        try:
            st = os.lstat(probe)
        except OSError as exc:
            return "cannot inspect %r (%s)" % (probe, exc.strerror)
        if st.st_uid not in (0, uid):
            return "%r is owned by another account" % probe
        if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH) and not (
            stat.S_ISDIR(st.st_mode) and st.st_mode & stat.S_ISVTX
        ):
            return "%r is writable by other accounts" % probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent
