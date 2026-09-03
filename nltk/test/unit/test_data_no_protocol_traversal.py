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
import os
from urllib.request import url2pathname

import pytest

from nltk.data import _reject_unsafe_no_protocol

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
MUST_REJECT = CONTROL_SPLIT + TRUNCATION + ENCODED + RAW


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
]


@pytest.mark.parametrize("name", MUST_PASS)
def test_legitimate_resource_passes(name):
    _reject_unsafe_no_protocol(name)  # must not raise


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
    ctrl = [
        "",
        "\t",
        "\n",
        "\r",
        "\v",
        "\f",
        "\x00",
        " ",
        "%09",
        "%0a",
        "%0d",
        "%00",
        "#",
        "?",
        "%23",
        "%3f",
    ]
    pre = ["", "foo/", "\t", " "]
    suf = ["", "/x", "#z", "?z"]
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
