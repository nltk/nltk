# Natural Language Toolkit: pathsec fast-path equivalence tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``validate_path`` must decide exactly as before, with less work.

* Root containment: it used to ask ``target == root or
  target.is_relative_to(root)`` of every allowed root, and ``is_relative_to``
  rebuilds the target's ancestors for each root.
  :func:`nltk.pathsec._within_any` looks each ancestor up in the set of roots
  once instead. The two are compared on every path of a small enumerated
  space, for both path flavours (so a Linux or macOS run checks the Windows
  rules too, and the reverse): case variants, a final sigma, prefixes that
  share leading characters but not a component, drives, UNC shares and
  relative paths.
* URL shapes: two timed regex matches ran on every path checked;
  :func:`nltk.pathsec._may_name_a_scheme` skips them when the first character
  rules both patterns out, checked against the real patterns for every
  first character.
"""

import itertools
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from nltk import pathsec
from nltk.pathsec import _within_any


def _reference(target, roots):
    return any(target == root or target.is_relative_to(root) for root in roots)


def _posix_paths():
    names = ["a", "A", "ab", "b", "a.b", "\u03a3", "\u03c3", "\u03c2"]
    paths = [PurePosixPath("/")]
    for n in range(1, 4):
        for parts in itertools.product(names[:4] if n == 3 else names, repeat=n):
            paths.append(PurePosixPath("/", *parts))
    paths += [PurePosixPath("a/b"), PurePosixPath("a"), PurePosixPath(".")]
    return paths


def _windows_paths():
    names = ["a", "A", "ab", "\u0391\u03a3", "\u03b1\u03c2", "\u03b1\u03c3"]
    anchors = ["C:\\", "c:\\", "D:\\", "\\\\srv\\share\\", "\\\\SRV\\Share\\"]
    paths = []
    for anchor in anchors:
        paths.append(PureWindowsPath(anchor))
        for n in range(1, 3):
            for parts in itertools.product(names, repeat=n):
                paths.append(PureWindowsPath(anchor, *parts))
    paths += [PureWindowsPath("a\\b"), PureWindowsPath("C:a"), PureWindowsPath(".")]
    return paths


@pytest.mark.parametrize("flavour", ["posix", "windows"])
def test_containment_matches_is_relative_to(flavour):
    """Every target against every single root, and against every pair of
    roots drawn from a spread of the space, is judged as before."""
    paths = _posix_paths() if flavour == "posix" else _windows_paths()
    for target in paths:
        for root in paths:
            assert _within_any(target, {root}) == _reference(target, [root]), (
                target,
                root,
            )
    spread = paths[:: max(1, len(paths) // 16)]
    for target in paths:
        for pair in itertools.combinations(spread, 2):
            assert _within_any(target, set(pair)) == _reference(target, pair), (
                target,
                pair,
            )
        assert _within_any(target, set()) is False


def test_lists_of_roots_still_work():
    """A caller (or a test) may hand over roots as any container: membership
    by equality gives the same answer."""
    root = PurePosixPath("/data/nltk")
    assert _within_any(PurePosixPath("/data/nltk/corpora/x"), [root])
    assert not _within_any(PurePosixPath("/data/nltk2/x"), [root])
    assert _within_any(root, (root,))


def test_scheme_patterns_are_the_ones_the_fast_path_reasons_about():
    assert pathsec._URL_SCHEME_RE.pattern == r"^\s*(?:https?|ftp)://"
    assert pathsec._FILE_SCHEME_RE.pattern == r"^\s*file:"


_TAILS = ["", "ttp://x", "TTP://x", "ttps://", "tp://x", "ile:", "ILE:/x", "://", "x"]


def test_scheme_fast_path_never_skips_a_match():
    """For every first character up to U+00FF and a few beyond, followed by
    tails that complete each scheme, the patterns match only where the fast
    path says they may; and every scheme spelling is still seen."""
    firsts = [chr(cp) for cp in range(0x100)] + ["\u2003", "\u3000", "\uff48"]
    for first in firsts:
        for tail in _TAILS:
            raw = first + tail
            matched = bool(
                pathsec._URL_SCHEME_RE.match(raw) or pathsec._FILE_SCHEME_RE.match(raw)
            )
            if matched:
                assert pathsec._may_name_a_scheme(raw), repr(raw)
    for raw in (
        "http://h/x",
        " HTTPS://h",
        "\tftp://h",
        "file:/x",
        "FILE:x",
        "\u3000file:",
    ):
        assert pathsec._may_name_a_scheme(raw), raw
    for raw in ("/srv/nltk_data/x", "C:\\nltk_data\\x", "\\\\srv\\s\\x", "~/x"):
        assert not pathsec._may_name_a_scheme(raw), raw


def test_url_shapes_are_still_refused():
    for raw in ("http://example.com/../x", "  ftp://h/x", "FILE:/etc/passwd?x=1"):
        with pytest.raises(PermissionError):
            pathsec.validate_path(raw)
        with pytest.raises((PermissionError, ValueError)):
            pathsec._reject_url_shaped(raw, "test")
