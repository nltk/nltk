# Natural Language Toolkit: data.load no-protocol traversal guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk.data._reject_unsafe_no_protocol screens a no-protocol resource path for
traversal before it is resolved. The screen must stay in lock-step with what
``url2pathname`` actually does to the string on the way to disk, across Python
versions:

* a literal deny-list (``../``, ``..$``, leading ``/``, ``\\``, drive-relative);
* an encoded re-check (``unquote`` once, because ``url2pathname`` percent-decodes);
* a rewritten-character re-check, because Python 3.14's WHATWG ``url2pathname``
  strips tab/LF/CR and truncates at ``#``/``?``, which can turn ``.\\n./x`` (no
  ``../``) into ``../x`` after the fact (CWE-22).

The core property is asserted directly against the real sink below: any string
the guard ACCEPTS must resolve, once ``url2pathname``-ed and joined to a data
root, INSIDE that root. No mocking: the guard and url2pathname run for real."""

import itertools
import ntpath
import os
import warnings
from urllib.request import url2pathname

import pytest

from nltk.data import _reject_unsafe_no_protocol

# nturl2path (the Windows url2pathname) is a TEST-ONLY oracle for Windows path
# semantics. It is deprecated in 3.14 and removed in 3.19, so import it defensively
# and skip the Windows-oracle assertions if it is gone. The guard in nltk/data.py does
# NOT depend on it: it refuses every ':'/'|' on all platforms instead.
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import nturl2path

    _HAVE_NTURL2PATH = True
except ImportError:  # pragma: no cover
    _HAVE_NTURL2PATH = False

# --- Traversals that MUST be rejected -----------------------------------------
# Literal control chars url2pathname (3.14 WHATWG) strips can splice a "..".
CONTROL_SPLIT = [
    "foo/.\t./x",
    "foo/.\n./x",
    "foo/.\r./x",
    ".\t./x",
    ".\n./x",
    ".\r./x",
    "foo/.\t\n.\r/x",  # several strippable controls at once
]
# Literal '#'/'?' truncate the tail, exposing a trailing "..".
TRUNCATION = ["foo/..#x", "foo/..?x", "foo/..#", "foo/..?"]
# Percent-encoded traversal that decodes to "../", "/", "\\" or a drive.
ENCODED = [
    "%2e%2e%2fetc%2fpasswd",
    "..%2fetc",
    "..%2Fetc",
    "%2fetc%2fpasswd",
    "foo%2f..%2f..%2fetc",
    "..%5cwindows",
    "..%5Cwindows",
    "c:%5cwindows",
]
# Raw absolute / drive / backslash / adjacent-dot traversal.
RAW = [
    "../etc/passwd",
    "..",
    "foo/../../etc",
    "/etc/passwd",
    "\\etc",
    "..\\windows",
    "c:/windows",
    "c:\\windows",
]
# Windows URL rewrites, refused on EVERY platform (determinism across the OS test
# matrix + defense-in-depth for nltk_data shared between platforms). On Windows
# url2pathname turns ':' or '|' into a drive ("a:b" -> "A:b" is drive-RELATIVE, so
# os.path.isabs is blind to it) or an alternate data stream, so the guard refuses
# every ':' and '|' outright (neither belongs in a no-protocol resource name). A
# trailing space/dot is stripped per component at open time, so ".. " (or "..%20")
# reconstitutes ".."; a dots-and-spaces-only component is refused. ":%2f" decodes to
# ":/" whose colon is refused (and on 3.13 nturl2path also raises: fail closed).
WINDOWS_REWRITE = [
    "a:b",
    "A:",
    "a|b",
    "c|/windows",
    "c|%2fwindows",
    "%2e%3a%2e/x",  # ".:./x": colon refused
    "..\x20",  # trailing space -> Windows opens ".."
    "foo/..\x20",
    "foo/..%20/bar",  # encoded trailing space
    "..%20",
    "foo/.\x20./x",  # space-split dots the Windows strip rejoins
    "//server/share/x",  # UNC
    ":%2f",  # decodes to ":/"; colon refused on every version
]
MUST_REJECT = CONTROL_SPLIT + TRUNCATION + ENCODED + RAW + WINDOWS_REWRITE


@pytest.mark.parametrize("bait", MUST_REJECT)
def test_traversal_candidate_is_rejected(bait):
    with pytest.raises(ValueError):
        _reject_unsafe_no_protocol(bait)


# --- Legitimate resource names that MUST pass (no over-blocking) --------------
MUST_PASS = [
    "corpora/brown/ca01",
    "tokenizers/punkt/english.pickle",
    "taggers/averaged_perceptron_tagger/model.json",
    "a.b.c/d_e-f/g1",
    "corpora/some.name.with.dots/file",  # dots that are not "../"
    "corpora/brown/ca01%20copy",  # a percent-encoded space is legitimate
    "corpora/name with space/file",  # an internal space is legitimate
    "corpora/UPPER_CASE/MixedCase123",
    "models/bllip_wsj_no_aux/parser",
    "chunkers/maxent_ne_chunker/PY3/english_ace_multiclass.pickle",
    "corpora/.hidden_dir/file",  # a leading-dot component is not a traversal
    "stemmers/rslp/step0.pt",
]


@pytest.mark.parametrize("name", MUST_PASS)
def test_legitimate_resource_passes(name):
    _reject_unsafe_no_protocol(name)  # must not raise


# --- Every control char / newline-like refused (future-strip proof) -----------
# The guard refuses ALL control characters and Unicode newline-likes, not only the
# tab/LF/CR that today's url2pathname strips, so a future url2pathname that strips
# a different one cannot rejoin ".." or expose a leading "/" past the raw check.
_ALL_CONTROLS = [chr(i) for i in range(0x00, 0x20)] + [
    "\x7f",
    "\x85",
    "\u2028",
    "\u2029",
]


@pytest.mark.parametrize("ctrl", _ALL_CONTROLS)
def test_control_char_split_traversal_is_refused(ctrl):
    # A control between the two dots would rejoin them into ".." if stripped.
    with pytest.raises(ValueError):
        _reject_unsafe_no_protocol("foo/." + ctrl + "./x")


@pytest.mark.parametrize("ctrl", _ALL_CONTROLS)
def test_control_char_before_absolute_is_refused(ctrl):
    # A leading control that url2pathname might strip would expose a leading "/".
    with pytest.raises(ValueError):
        _reject_unsafe_no_protocol(ctrl + "/etc/passwd")


# --- Core property: accepted => the real sink stays inside the root -----------
_ROOT = os.path.realpath(os.path.join(os.sep, "data", "nltk_root"))


def _sink_escapes(payload):
    """True if url2pathname(payload) joined to the data root escapes it, i.e. the
    exact thing find() does after the guard passes."""
    try:
        resolved = url2pathname(payload)
    except (ValueError, OSError):
        return False
    joined = os.path.normpath(os.path.join(_ROOT, resolved))
    return not (joined == _ROOT or joined.startswith(_ROOT + os.sep))


def _fuzz_candidates():
    dots = [".", "%2e", "%2E", "%252e"]
    seps = ["/", "\\", "%2f", "%5c"]
    ctrl = (
        [""]
        + [chr(i) for i in range(0x20)]  # every C0 control
        + ["\x7f", "\x85", "\u2028", "\u2029", " "]  # DEL, NEL, separators, space
        + ["%09", "%0a", "%0d", "%00", "%0b", "%0c", "#", "?", "%23", "%3f"]  # encoded
        # Windows drive/UNC rewrites and the trailing-strip vector:
        + [":", "|", "%3a", "%7c", "c:", "c|", "\\\\", "//", "%20"]
    )
    pre = ["", "foo/", "\t", " ", ":", "|"]
    suf = ["", "/x", "#z", "?z", " ", "%20", "."]
    for d1, c, d2, s, p, x in itertools.product(dots, ctrl, dots, seps, pre, suf):
        yield p + d1 + c + d2 + s + x


def test_guard_pass_implies_sink_cannot_escape_root():
    # The invariant that makes the guard sufficient: every string it ACCEPTS must
    # resolve inside the root through the real url2pathname sink. Fuzz thousands of
    # dot/separator/control/encoding combinations on THIS interpreter (so the
    # actual, version-specific url2pathname is exercised) and assert no accepted
    # candidate escapes.
    escaped = []
    for cand in _fuzz_candidates():
        try:
            _reject_unsafe_no_protocol(cand)
        except ValueError:
            continue  # rejected: safe
        if _sink_escapes(cand):
            escaped.append((cand, url2pathname(cand)))
    assert not escaped, f"guard accepted {len(escaped)} traversal(s): {escaped[:5]}"


# --- Cross-platform: accepted => neither the POSIX nor the Windows sink escapes ---
# The guard runs on one OS at a time, but nltk_data is shared between them and CI
# spans macOS/Ubuntu/Windows, so it refuses anything that escapes under EITHER
# platform's url2pathname. Model the Windows sink here (nturl2path/ntpath as a
# test-only oracle) and assert every accepted string stays inside a root under BOTH.
# If nturl2path is gone (Python 3.19+), the Windows oracle degrades to "never
# escapes" so the POSIX-only assertions still run.
_NT_ROOT = "C:\\data\\nltk_root"


def _nt_sink_escapes(payload):
    """True if the WINDOWS sink (nturl2path + ntpath), including the open-time
    trailing-dot/space strip, would resolve payload outside an nt data root."""
    if not _HAVE_NTURL2PATH:
        return False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            resolved = nturl2path.url2pathname(payload)
    except Exception:
        return False  # unparseable: the guard fails closed, nothing reaches disk
    joined = ntpath.normpath(ntpath.join(_NT_ROOT, resolved))
    parts = joined.split("\\")
    stripped = ntpath.normpath(
        "\\".join(c if c == ".." else c.rstrip(" .") for c in parts)
    )
    return any(
        not (cand == _NT_ROOT or cand.startswith(_NT_ROOT + "\\"))
        for cand in (joined, stripped)
    )


def test_guard_pass_implies_neither_platform_sink_escapes():
    escaped = []
    for cand in _fuzz_candidates():
        try:
            _reject_unsafe_no_protocol(cand)
        except ValueError:
            continue  # rejected: safe on every platform
        if _sink_escapes(cand) or _nt_sink_escapes(cand):
            escaped.append(cand)
    assert not escaped, f"guard accepted cross-platform traversal(s): {escaped[:5]}"


# Exotic URL/path normalization vectors kept in the harness so a regression that
# starts decoding/normalizing any of them is caught. Each is EITHER a real escape
# the guard must reject OR contained under both platforms (an overlong-UTF-8 byte
# that does not decode to a separator, a Unicode look-alike that is not an ASCII
# separator, double-encoding that only decodes once, a zero-width char that does not
# reconstitute ".."). The invariant asserted below is the same one that matters:
# if the guard ACCEPTS it, neither the POSIX nor the Windows sink may escape.
_EXOTIC_CANDIDATES = [
    # overlong / invalid UTF-8 that could decode to a separator or dot
    "..%c0%af..",
    "%c0%ae%c0%ae/x",
    "..%e0%80%afetc",
    "%c1%9c..",
    "..%c0%5c",
    # Unicode / fullwidth look-alike separators and dots (not ASCII separators).
    # Written with explicit \u escapes so no invisible/look-alike char sits in source.
    "..\uff0f..",  # U+FF0F fullwidth solidus
    "\u2044etc",  # fraction slash
    "\u2215etc",  # division slash
    "..\uff3cwin",  # U+FF3C fullwidth reverse solidus
    "\uff0e\uff0e/x",  # U+FF0E fullwidth full stops
    "\u2024\u2024/x",  # U+2024 one dot leader
    # alternate data streams / reserved device names (Windows)
    "foo:bar",
    "x:stream:$DATA",
    "con:x",
    "foo::$INDEX_ALLOCATION",
    "a:$DATA",
    # multi / deep percent-encoding (url2pathname only decodes once)
    "%252e%252e%252fetc",
    "%25%32%65%25%32%65/x",
    "..%25%32%66etc",
    # zero-width / bidi / BOM spliced into a would-be ".." (explicit \u escapes)
    "\ufeff../x",  # BOM
    "..\u200b/x",  # zero-width space
    ".\u200d./x",  # zero-width joiner
    "..\u2060/x",  # word joiner
    # trailing dot(s)/space combinations (Windows open-time strip)
    "foo/...",
    "foo/.../..",
    "foo/ ..",
    "foo/.. .",
    "foo/. ",
    "x/.. /..",
    # mixed drive / pipe encodings
    "%63%7c/win",
    "c%7c/win",
    "%41%3a",
    "c:%2e%2e",
]


@pytest.mark.parametrize("cand", _EXOTIC_CANDIDATES)
def test_exotic_vector_accepted_only_if_contained_on_both_platforms(cand):
    # Never crash (only ValueError), and if accepted it must be contained under
    # BOTH the POSIX and the Windows sink.
    try:
        _reject_unsafe_no_protocol(cand)
    except ValueError:
        return  # rejected: safe on every platform
    except Exception as exc:  # pragma: no cover
        raise AssertionError(f"guard raised {type(exc).__name__} on {cand!r}: {exc}")
    assert not _sink_escapes(cand), f"POSIX sink escapes for accepted {cand!r}"
    assert not _nt_sink_escapes(cand), f"Windows sink escapes for accepted {cand!r}"


def test_guard_only_ever_raises_valueerror():
    # A hostile name must never crash the guard with anything but ValueError.
    # nturl2path raises IndexError on malformed drive syntax such as ":%2f"; the
    # guard must catch it and fail closed, not propagate a surprise exception (DoS).
    for cand in list(_fuzz_candidates()) + [
        ":%2f",
        ":%2f%2fx",
        "%3a%2f",
        "|%2f",
        ":|/x",
        "|:/x",
    ]:
        try:
            _reject_unsafe_no_protocol(cand)
        except ValueError:
            pass
        except Exception as exc:  # pragma: no cover - this is the failure we guard
            raise AssertionError(
                f"guard raised {type(exc).__name__} (not ValueError) on {cand!r}: {exc}"
            )
