# -*- coding: utf-8 -*-
# Natural Language Toolkit: Path, archive, URL and executable checks
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
The path-trust checks of the 3.4 maintenance line, laid out and named as in
the 3.10 line's ``nltk.pathsec`` so a reader of either tree finds the same
function at the same sink. The 3.10 module is a full sandbox; this one keeps
only what the in-place fixes of this line need, with the same semantics
where the names coincide:

* :func:`validate_path`: a path joined from caller input stays inside its
  root once links are resolved (CWE-22, CWE-59).
* :func:`validate_tool_path`: a path handed to an external tool may not
  step upward, be a link, or be a hardlinked write target (CWE-59, CWE-73).
* :func:`untrusted_executable_reason` and
  :func:`resolve_trusted_executable`: a binary must sit where only this
  account or root can write (CWE-426).
* :func:`urlopen`: only http and https may be fetched (CWE-918).
* :func:`validate_zip_member`: an archive member may not escape the
  extraction root nor another package's directory (Zip-Slip, CWE-22).
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import stat
import sys

from six import binary_type, string_types, text_type
from six.moves.urllib.parse import urlsplit
from six.moves.urllib.request import urlopen as _urlopen

__all__ = [
    "SecurityError",
    "TrustError",
    "validate_path",
    "validate_tool_path",
    "untrusted_executable_reason",
    "resolve_trusted_executable",
    "find_on_path",
    "urlopen",
    "validate_zip_member",
]


class SecurityError(ValueError):
    """Raised when a path, archive member or URL would cross a boundary."""


class TrustError(OSError):
    """Raised when a binary is not safe to execute (as in the 3.10 line)."""


# ----------------------------------------------------------------------
# Paths (CWE-22, CWE-59)
# ----------------------------------------------------------------------


def _fspath(path):
    """``os.fspath`` for both interpreters (text, bytes or a path object)."""
    if isinstance(path, (text_type, binary_type)):
        return path
    getter = getattr(type(path), "__fspath__", None)
    if getter is None:
        raise TypeError("expected a path, not %s" % type(path).__name__)
    return getter(path)


def _text(path):
    path = _fspath(path)
    if isinstance(path, binary_type) and not isinstance(path, text_type):
        return path.decode(sys.getfilesystemencoding() or "utf-8")
    return path


def _realpath(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def has_parent_reference(name):
    """True when a slash- or backslash-separated *name* steps upward."""
    return any(part == ".." for part in re.split(r"[\\/]+", name))


def validate_path(path_input, context="NLTK", required_root=None):
    """Return *path_input* when it is acceptable, else raise :class:`SecurityError`.

    With *required_root*, the path must lie inside that root once every link
    is resolved: a ``..`` component, an absolute path elsewhere, or a link
    pointing outside the root are refused (CWE-22, CWE-59). Without a root
    only a NUL byte is refused. *context* names the caller in the message.
    """
    text = _text(path_input)
    if "\x00" in text:
        raise SecurityError("%s: path holds a NUL byte: %r" % (context, text))
    if required_root is not None:
        real_root = _realpath(required_root)
        real_path = _realpath(text)
        if not (real_path == real_root or real_path.startswith(real_root.rstrip(os.sep) + os.sep)):
            raise SecurityError(
                "%s: %r escapes its root %r" % (context, text, required_root)
            )
    return path_input


def validate_tool_path(path_input, context="NLTK tool", for_write=False):
    """Return the absolute path a wrapper may hand to an external tool.

    The tool opens the path natively, outside any check this library can
    make later, so it is bounded here: no ``..`` component; the final name
    must not be a symbolic link; every symbolic link on the way must belong
    to this account or root (a system layout such as ``/var`` on macOS is
    fine, a link planted by another account in a shared directory is not);
    and a write target that exists must be a regular file with a single
    name, so a planted link or hardlink cannot redirect the write
    (CWE-59, CWE-73). Returns the absolute path as a string.
    """
    text = _text(path_input)
    if "\x00" in text:
        raise SecurityError("%s: path holds a NUL byte: %r" % (context, text))
    if has_parent_reference(text):
        raise SecurityError("%s: path steps upward with '..': %r" % (context, text))
    absolute = os.path.abspath(text)
    if os.path.islink(absolute):
        raise SecurityError("%s: path is a symbolic link: %r" % (context, text))
    if os.name == "posix":
        uid = os.geteuid()
        probe = absolute
        while True:
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            if os.path.islink(parent):
                owner = os.lstat(parent).st_uid
                if owner not in (0, uid):
                    raise SecurityError(
                        "%s: path passes through a link owned by another account: %r"
                        % (context, parent)
                    )
            probe = parent
    if for_write and os.path.lexists(absolute):
        st = os.lstat(absolute)
        if not stat.S_ISREG(st.st_mode):
            raise SecurityError("%s: not a regular file: %r" % (context, text))
        if getattr(st, "st_nlink", 1) > 1:
            raise SecurityError(
                "%s: the file has more than one name (hardlinked): %r" % (context, text)
            )
    return absolute


# ----------------------------------------------------------------------
# Executables (CWE-426)
# ----------------------------------------------------------------------


def untrusted_executable_reason(target):
    """Why *target* is not a trustworthy binary to execute, or None.

    The binary and every directory above it must be owned by this account
    or root and be writable by nobody else; a relative path is refused too,
    since it would resolve against the current directory (CWE-426).
    """
    if not os.path.isabs(target):
        return "the path is relative and would resolve against the current directory"
    real = os.path.realpath(target)
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


def resolve_trusted_executable(target, context="executable"):
    """Return *target* when :func:`untrusted_executable_reason` accepts it,
    else raise :class:`TrustError` naming the reason (CWE-426)."""
    if target is None:
        raise TrustError("%s not found" % context)
    reason = untrusted_executable_reason(target)
    if reason is not None:
        raise TrustError("refusing to run %s %r: %s" % (context, target, reason))
    return target


def find_on_path(name):
    """The first regular file named *name* in the PATH directories, or None;
    a bare program name is never handed to a spawn unresolved."""
    if os.path.isabs(name):
        return name
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    return None


# ----------------------------------------------------------------------
# Network (CWE-918)
# ----------------------------------------------------------------------

_ALLOWED_SCHEMES = ("http", "https")


def urlopen(url, *args, **kwargs):
    """``urllib``'s ``urlopen`` for http and https only: a file, ftp or data
    URL that an index or a redirect could smuggle is refused (CWE-918)."""
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise SecurityError("URL %r: only http and https may be fetched" % (url,))
    return _urlopen(url, *args, **kwargs)


# ----------------------------------------------------------------------
# Archives (CWE-22)
# ----------------------------------------------------------------------

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def validate_zip_member(name, root, expected_root=None):
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
    validate_path(target, "archive member %r" % name, required_root=root)
    probe = root
    for part in parts[:-1]:
        probe = os.path.join(probe, part)
        if os.path.islink(probe):
            raise SecurityError(
                "archive member %r would write through the link %r" % (name, probe)
            )
    return target
