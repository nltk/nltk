# Natural Language Toolkit: zip member safety under both platforms' rules
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""A zip member's safety depends on whose separator rules apply.

``..\\..\\x`` is a single ordinary filename on POSIX and cannot traverse, but on
Windows the backslash IS a separator and the same member escapes. ``C:/x`` is
likewise a plain relative name on POSIX and an absolute path on Windows.

``_zip_member_is_unsafe`` therefore normalises only when ``os.path.altsep`` is
set, which is ``'/'`` on Windows and ``None`` on POSIX. That is easy to read as
a bug ("why isn't it always normalising?") and easy to 'fix' into an over-block
that refuses legitimate POSIX filenames, so this pins BOTH answers by swapping
in each platform's path module. It means a Linux CI run still checks the Windows
behaviour, which no single-platform test can.
"""

import ntpath
import os
import posixpath

import pytest

from nltk import pathsec

# (member, unsafe-on-posix, unsafe-on-windows)
_MEMBERS = [
    ("plain.txt", False, False),
    ("good/sub/file.txt", False, False),
    ("../../outside/PWNED.txt", True, True),
    ("/abs/PWNED.txt", True, True),
    ("ok\x00/../../P.txt", True, True),
    ("..\\..\\outside\\PWNED.txt", False, True),
    ("C:/PWNED.txt", False, True),
    ("C:\\PWNED.txt", False, True),
]


def _verdict_under(module, member):
    """Run the check with a given platform's path semantics."""
    saved_altsep, saved_splitdrive = os.path.altsep, os.path.splitdrive
    os.path.altsep, os.path.splitdrive = module.altsep, module.splitdrive
    try:
        return pathsec._zip_member_is_unsafe(member)
    finally:
        os.path.altsep, os.path.splitdrive = saved_altsep, saved_splitdrive


@pytest.mark.parametrize(
    "member, unsafe_posix, unsafe_windows",
    _MEMBERS,
    ids=[m.replace("\\", "bs").replace("/", "_")[:24] for m, _, _ in _MEMBERS],
)
def test_member_safety_matches_each_platforms_rules(
    member, unsafe_posix, unsafe_windows
):
    assert _verdict_under(posixpath, member) is unsafe_posix
    assert _verdict_under(ntpath, member) is unsafe_windows


def test_backslash_members_are_only_dangerous_on_windows():
    """Stated explicitly because it is the counter-intuitive half.

    Refusing these on POSIX would be an over-block: a file really can be named
    ``..\\..\\x`` there, and extracting it creates that one file.
    """
    member = "..\\..\\outside\\PWNED.txt"
    assert _verdict_under(ntpath, member) is True
    assert _verdict_under(posixpath, member) is False


def test_extraction_refuses_traversing_members_end_to_end(pathsec_sandbox):
    """The real extractor, not just the predicate."""
    import zipfile

    root, outside = pathsec_sandbox
    archive = str(root / "evil.zip")
    for member in ("../../outside/PWNED.txt", "/tmp/PWNED_ABS.txt", ".."):
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr(member, "PWNED")
        destination = str(root / "unpacked")
        with pytest.raises((PermissionError, ValueError)):
            with pathsec.ZipFile(archive) as handle:
                handle.extractall(destination)
        assert not (outside / "PWNED.txt").exists()
        assert not os.path.exists("/tmp/PWNED_ABS.txt")


def test_extraction_still_works_for_ordinary_members(pathsec_sandbox):
    """Over-block control."""
    import zipfile

    root, _outside = pathsec_sandbox
    archive = str(root / "good.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("sub/dir/file.txt", "fine")
    destination = str(root / "unpacked")
    with pathsec.ZipFile(archive) as handle:
        handle.extractall(destination)
    assert (root / "unpacked" / "sub" / "dir" / "file.txt").read_text() == "fine"
