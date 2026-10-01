# Natural Language Toolkit: zip extraction TOCTOU hardening
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Zip extraction must not follow a symlink at the write target.

validate_zip_archive resolves each member and refuses one that escapes, but
between that resolution and the write there is a TOCTOU window: a local attacker
who can write inside the extraction root can swap a directory component for a
symlink pointing outside, and the stdlib extractor's plain open(target, "wb")
follows it. pathsec.ZipFile._extract_member writes the leaf through an
O_NOFOLLOW | O_EXCL opener, so a symlink at the final component (raced in or
pre-planted) is refused rather than followed.
"""

import os
import shutil
import tempfile
import zipfile

import pytest

import nltk.data
from nltk import pathsec


@pytest.fixture
def sandbox(monkeypatch):
    base = tempfile.mkdtemp(prefix=".nltk_toctou_", dir=os.path.expanduser("~"))
    root = os.path.join(base, "root")
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


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="requires O_NOFOLLOW")
def test_raw_zipfile_would_follow_a_symlinked_parent(sandbox):
    """Establishes the primitive the guard defends against: the stdlib extractor
    writes through a symlinked parent directory."""
    root, outside = sandbox
    archive = os.path.join(root, "a.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("pkg/sub/PWNED.txt", "PWNED")
    os.makedirs(os.path.join(root, "pkg"))
    os.symlink(outside, os.path.join(root, "pkg", "sub"))
    with zipfile.ZipFile(archive) as handle:  # raw stdlib
        handle.extract("pkg/sub/PWNED.txt", root)
    assert os.path.exists(os.path.join(outside, "PWNED.txt"))


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="requires O_NOFOLLOW")
def test_pathsec_extract_refuses_a_symlinked_leaf_parent(sandbox):
    root, outside = sandbox
    archive = os.path.join(root, "a.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("pkg/sub/PWNED.txt", "PWNED")
    os.makedirs(os.path.join(root, "pkg"))
    os.symlink(outside, os.path.join(root, "pkg", "sub"))
    with pytest.raises((PermissionError, OSError, ValueError)):
        with pathsec.ZipFile(archive) as handle:
            handle.extract("pkg/sub/PWNED.txt", root)
    assert not os.path.exists(os.path.join(outside, "PWNED.txt"))


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="requires O_NOFOLLOW")
def test_pathsec_extract_refuses_a_pre_planted_symlink_leaf(sandbox):
    root, outside = sandbox
    archive = os.path.join(root, "a.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("x", "PWNED")
    os.makedirs(os.path.join(root, "p"))
    victim = os.path.join(outside, "victim")
    # archive member p/leaf will target the pre-planted symlink at <root>/p/leaf
    archive2 = os.path.join(root, "b.zip")
    with zipfile.ZipFile(archive2, "w") as handle:
        handle.writestr("p/leaf", "PWNED")
    os.symlink(victim, os.path.join(root, "p", "leaf"))
    with pytest.raises((PermissionError, OSError, ValueError)):
        with pathsec.ZipFile(archive2) as handle:
            handle.extract("p/leaf", root)
    assert not os.path.exists(victim)


def test_ordinary_extraction_still_works(sandbox):
    """Over-block control: nested dirs, top-level files, and a benign re-extract
    onto existing files."""
    root, _outside = sandbox
    archive = os.path.join(root, "g.zip")
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("a/b/c.txt", "hello")
        handle.writestr("top.txt", "x")
    destination = os.path.join(root, "out")
    with pathsec.ZipFile(archive) as handle:
        handle.extractall(destination)
    with open(os.path.join(destination, "a", "b", "c.txt")) as fh:
        assert fh.read() == "hello"
    # re-extract must not fail on the now-existing regular files
    with pathsec.ZipFile(archive) as handle:
        handle.extractall(destination)
