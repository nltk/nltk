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
    "check_tool_path",
    "safe_xml_parse",
    "safe_xml_fromstring",
    "trusted_executable",
    "find_on_path",
    "sanitize_csv_field",
    "check_json_depth",
    "token_hex",
    "html_escape",
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
        return codecs.escape_decode(body.encode("latin-1"))[0]
    if PY2 and "u" not in prefix:
        # what eval gave on 2.7: a native byte string with the escapes resolved
        return codecs.escape_decode(body.encode("utf-8"))[0]
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


# ----------------------------------------------------------------------
# Web helpers (CWE-79, CWE-306)
# ----------------------------------------------------------------------


def token_hex(nbytes=16):
    """A random hex token from the OS entropy source."""
    return codecs.encode(os.urandom(nbytes), "hex").decode("ascii")


def html_escape(text):
    """Escape ``&``, ``<``, ``>``, double and single quotes for HTML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# ----------------------------------------------------------------------
# CSV and JSON (CWE-1236, CWE-674)
# ----------------------------------------------------------------------

_CSV_FORMULA_LEADS = ("=", "+", "-", "@", "|", "%", "\t", "\r")
_PLAIN_NUMBER_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")


def sanitize_csv_field(value):
    """Neutralise a spreadsheet formula lead at the start of a CSV cell.

    A cell whose first non-blank character is one of ``= + - @ | %`` (or a
    tab or carriage return) is evaluated as a formula by spreadsheets
    (CWE-1236); the industry neutralisation prefixes an apostrophe. Numbers
    and plain numeric strings pass unchanged; other values are returned as
    they were.
    """
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, binary_type) and not isinstance(value, text_type):
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError:
            return value
    else:
        text = value if isinstance(value, text_type) else text_type(value)
    stripped = text.lstrip(" ")
    if stripped.startswith(_CSV_FORMULA_LEADS) and not _PLAIN_NUMBER_RE.match(stripped):
        return "'" + text
    return value


MAX_JSON_DEPTH = 100


def check_json_depth(text, limit=MAX_JSON_DEPTH):
    """Refuse a JSON text nested deeper than *limit*: the recursive decoder
    would otherwise overflow the stack on a crafted line (CWE-674)."""
    if isinstance(text, binary_type) and not isinstance(text, text_type):
        text = text.decode("utf-8", "replace")
    depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            if depth > limit:
                raise SecurityError("JSON nested deeper than %d levels" % limit)
        elif ch in "]}":
            depth -= 1
    return text


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


def trusted_executable(path, what="executable"):
    """Return *path* when :func:`untrusted_executable_reason` accepts it,
    else raise :class:`LookupError` naming the reason (CWE-426)."""
    if path is None:
        raise LookupError("%s not found" % what)
    reason = untrusted_executable_reason(path)
    if reason is not None:
        raise LookupError("refusing to run %s %r: %s" % (what, path, reason))
    return path


# ----------------------------------------------------------------------
# XML (CWE-776, CWE-611, CWE-674)
# ----------------------------------------------------------------------

#: Ceilings on a parsed document: elements, and the depth of the tree.
MAX_XML_ELEMENTS = 20000000
MAX_XML_DEPTH = 1000

try:  # the vendor library when installed; the expat fence below otherwise
    import defusedxml.ElementTree as _defused_etree
except ImportError:  # pragma: no cover
    _defused_etree = None

from xml.etree import ElementTree as _ElementTree
from xml.parsers import expat as _expat


class XMLForbidden(ValueError):
    """Raised for an entity declaration or an external reference."""


def _fenced_expat_parse(data):
    """Build an ElementTree from *data* with an expat parser whose entity
    and external-reference handlers refuse: a document can then neither
    expand (billion laughs, CWE-776) nor fetch (XXE, CWE-611). Names are
    produced in ElementTree's ``{uri}local`` form."""
    builder = _ElementTree.TreeBuilder()
    parser = _expat.ParserCreate(None, "}")
    parser.ordered_attributes = True
    parser.buffer_text = True

    def fixtext(text):
        # ElementTree on 2.7 returns ASCII-only content as a native str
        if PY2 and isinstance(text, text_type):
            try:
                return text.encode("ascii")
            except UnicodeEncodeError:
                return text
        return text

    def fix(name):
        return fixtext("{" + name if "}" in name else name)

    def start(name, attrs):
        attrib = {}
        for i in range(0, len(attrs), 2):
            attrib[fix(attrs[i])] = fixtext(attrs[i + 1])
        builder.start(fix(name), attrib)

    def forbid_entity(name, is_parameter, value, base, sysid, pubid, notation):
        raise XMLForbidden("entity declarations are not allowed (%r)" % (name,))

    def forbid_external(context, base, sysid, pubid):
        raise XMLForbidden("external entity references are not allowed")

    def forbid_unparsed(name, base, sysid, pubid, notation):
        raise XMLForbidden("unparsed entity declarations are not allowed")

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: builder.end(fix(name))
    parser.CharacterDataHandler = lambda data: builder.data(fixtext(data))
    parser.EntityDeclHandler = forbid_entity
    parser.UnparsedEntityDeclHandler = forbid_unparsed
    parser.ExternalEntityRefHandler = forbid_external
    try:
        parser.Parse(data, True)
    except _expat.ExpatError as exc:
        raise _ElementTree.ParseError(str(exc))
    return builder.close()


def _check_tree(root):
    """Refuse a tree deeper than ``MAX_XML_DEPTH`` or larger than
    ``MAX_XML_ELEMENTS`` (CWE-674, CWE-400)."""
    count = 0
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if depth > MAX_XML_DEPTH:
            raise XMLForbidden("XML nested deeper than %d elements" % MAX_XML_DEPTH)
        if count > MAX_XML_ELEMENTS:
            raise XMLForbidden("XML holds more than %d elements" % MAX_XML_ELEMENTS)
        for child in list(node):
            stack.append((child, depth + 1))
    return root


def _read_source(source):
    if hasattr(source, "read"):
        return read_bounded(source, what="XML document")
    with io.open(source, "rb") as fh:
        return read_bounded(fh, what="XML document")


def safe_xml_parse(source):
    """``ElementTree.parse`` that refuses entities and external references
    and bounds the tree it builds. *source* is a path or a binary stream."""
    if _defused_etree is not None:
        tree = _defused_etree.parse(source, forbid_dtd=False, forbid_entities=True, forbid_external=True)
        _check_tree(tree.getroot())
        return tree
    root = _fenced_expat_parse(_read_source(source))
    return _ElementTree.ElementTree(_check_tree(root))


def safe_xml_fromstring(text):
    """``ElementTree.fromstring`` with the same refusals and bounds."""
    if _defused_etree is not None:
        root = _defused_etree.fromstring(text, forbid_dtd=False, forbid_entities=True, forbid_external=True)
        return _check_tree(root)
    if isinstance(text, text_type):
        text = text.encode("utf-8")
    return _check_tree(_fenced_expat_parse(text))


# ----------------------------------------------------------------------
# Paths handed to external tools (CWE-59, CWE-73)
# ----------------------------------------------------------------------


def check_tool_path(path, for_write=False, what="tool path"):
    """Return the absolute *path* a wrapper may hand to an external tool.

    The tool opens the path natively, outside any check this library can
    make later, so it is bounded here: no ``..`` component; the final name
    must not be a symbolic link; every symbolic link on the way must belong
    to this account or root (a system layout such as ``/var`` on macOS is
    fine, a link planted by another account in a shared directory is not);
    and a write target that exists must be a regular file with a single
    name, so a planted link or hardlink cannot redirect the write
    (CWE-59, CWE-73). Returns the absolute path as a string.
    """
    text = fspath(path) if not isinstance(path, string_types) else path
    if isinstance(text, binary_type) and not isinstance(text, text_type):
        text = fsdecode_native(text)
    if "\x00" in text:
        raise SecurityError("%s holds a NUL byte: %r" % (what, text))
    if has_parent_reference(text):
        raise SecurityError("%s steps upward with '..': %r" % (what, text))
    absolute = os.path.abspath(text)
    if os.path.islink(absolute):
        raise SecurityError("%s is a symbolic link: %r" % (what, text))
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
                        "%s passes through a link owned by another account: %r"
                        % (what, parent)
                    )
            probe = parent
    if for_write and os.path.lexists(absolute):
        st = os.lstat(absolute)
        if not stat.S_ISREG(st.st_mode):
            raise SecurityError("%s is not a regular file: %r" % (what, text))
        if getattr(st, "st_nlink", 1) > 1:
            raise SecurityError("%s has more than one name (hardlinked): %r" % (what, text))
    return absolute


def fspath(path):
    """``os.fspath`` for both interpreters (text, bytes or a path object)."""
    if isinstance(path, (text_type, binary_type)):
        return path
    getter = getattr(type(path), "__fspath__", None)
    if getter is None:
        raise TypeError("expected a path, not %s" % type(path).__name__)
    return getter(path)


def fsdecode_native(value):
    return value.decode(sys.getfilesystemencoding() or "utf-8")
