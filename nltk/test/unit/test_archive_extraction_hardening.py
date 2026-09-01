# Natural Language Toolkit: archive extraction hardening
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Archive attacks beyond a plain ``..`` member.

Covers the write/read-through, entry-count and decompression-bomb classes. One
result is worth stating rather than assuming: Python's ``zipfile`` never creates
a symlink on extract; a symlink member is written as a regular file whose
content is the link-target string. So the zip symlink-write-through attack is
structurally impossible through ``extractall``, and the test pins that behaviour
so a future move to a symlink-honouring extractor would surface here.
"""

import gzip
import os
import shutil
import tempfile
import zipfile

import pytest

import nltk.data
from nltk import pathsec


@pytest.fixture
def sandbox(monkeypatch):
    base = tempfile.mkdtemp(prefix=".nltk_arc_", dir=os.path.expanduser("~"))
    root = os.path.join(base, "nltk_data")
    outside = os.path.join(base, "outside")
    os.makedirs(root)
    os.makedirs(outside)
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield root, outside
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_a_symlink_member_is_written_as_a_regular_file(sandbox):
    root, _outside = sandbox
    archive = os.path.join(root, "sym.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        info = zipfile.ZipInfo("passwd_link")
        info.external_attr = 0o120777 << 16  # S_IFLNK
        handle.writestr(info, "/etc/passwd")
    destination = os.path.join(root, "unpacked")
    with pathsec.ZipFile(archive) as handle:
        handle.extractall(destination)
    extracted = os.path.join(destination, "passwd_link")
    assert not os.path.islink(extracted), "extractall created a symlink"
    with open(extracted) as fh:
        assert fh.read() == "/etc/passwd"


def test_symlink_write_through_cannot_escape(sandbox):
    """Two-member layout: a symlink then a file written through it. zipfile
    writes the symlink as a plain file, so the second member cannot descend into
    it and the write stays contained (or raises)."""
    root, outside = sandbox
    archive = os.path.join(root, "wt.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        info = zipfile.ZipInfo("sub")
        info.external_attr = 0o120777 << 16
        handle.writestr(info, outside)
        handle.writestr("sub/PWNED.txt", "PWNED")
    destination = os.path.join(root, "wt_out")
    try:
        with pathsec.ZipFile(archive) as handle:
            handle.extractall(destination)
    except (OSError, PermissionError, ValueError):
        pass  # NotADirectoryError etc. -- the escape simply cannot happen
    assert not os.path.exists(os.path.join(outside, "PWNED.txt"))


def test_a_high_entry_count_zip_is_refused(sandbox):
    root, _outside = sandbox
    archive = os.path.join(root, "many.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        for index in range(150000):
            handle.writestr(f"f{index}", "")
    with pytest.raises((PermissionError, ValueError)):
        with pathsec.ZipFile(archive):
            pass


def test_a_gzip_decompression_bomb_is_refused(sandbox):
    root, _outside = sandbox
    bomb = os.path.join(root, "bomb.gz")
    with gzip.open(bomb, "wb") as handle:
        handle.write(b"\0" * (200 * 1024 * 1024))
    assert os.path.getsize(bomb) < 1_000_000  # tiny on disk
    from nltk.data import GzipFileSystemPathPointer

    with pytest.raises((PermissionError, ValueError)):
        GzipFileSystemPathPointer(bomb).open().read()


def test_ordinary_archives_still_extract(sandbox):
    """Over-block control."""
    root, _outside = sandbox
    archive = os.path.join(root, "good.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("sub/dir/file.txt", "fine")
    destination = os.path.join(root, "good_out")
    with pathsec.ZipFile(archive) as handle:
        handle.extractall(destination)
    with open(os.path.join(destination, "sub", "dir", "file.txt")) as fh:
        assert fh.read() == "fine"
