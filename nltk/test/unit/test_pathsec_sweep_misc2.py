# Natural Language Toolkit: pathsec sweep attack tests (misc modules, part 2)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path-traversal attack tests for the caller-controlled file sink hardened in
``nltk.sem.util.read_sents``.

The chat80 / tbl.demo sinks in this file set are already exercised by
``test_pathsec_sweep_misc.py``; this module covers the remaining hardened public
API; ``read_sents``, which opens a caller-supplied path through the pathsec
sentinel; so that a read outside the NLTK data sandbox is refused while a
legitimate read inside it still works (GHSA-8mgp-746c-j5xp).
"""

import os
import pathlib
import shutil
import tempfile
import types

import pytest

import nltk.data
import nltk.pathsec as pathsec


@pytest.fixture
def sandbox():
    """Enforce pathsec with a single throwaway data root and yield both that
    (trusted) root and an *outside* target directory the sandbox must refuse.

    The outside directory is a fresh dir under the real home directory; NOT a
    temp dir, because on macOS the private per-user system temp dir *is* an
    allowed root (``pathsec._get_allowed_roots``), which would make a temp-dir
    "attack" spuriously succeed.
    """
    saved_enforce = pathsec.ENFORCE
    saved_paths = list(nltk.data.path)
    saved_cwd = os.getcwd()

    data_root = tempfile.mkdtemp(prefix="nltk_sweep_sandbox2_")
    outside = pathlib.Path.home() / f".nltk_sweep_misc2_{os.getpid()}"
    outside.mkdir(parents=True, exist_ok=True)

    pathsec.ENFORCE = True
    nltk.data.path[:] = [data_root]
    pathsec._ALLOWED_ROOTS_CACHE = None
    pathsec._LAST_DATA_PATHS = None

    try:
        yield types.SimpleNamespace(data_root=pathlib.Path(data_root), outside=outside)
    finally:
        pathsec.ENFORCE = saved_enforce
        nltk.data.path[:] = saved_paths
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        os.chdir(saved_cwd)
        shutil.rmtree(outside, ignore_errors=True)
        shutil.rmtree(data_root, ignore_errors=True)


def test_negative_control_open_outside_raises(sandbox):
    """The sandbox is wired correctly: a plain pathsec.open() read of the outside
    target must be refused even though the file exists."""
    target = sandbox.outside / "neg_control.txt"
    target.write_text("hello\n")
    with pytest.raises(PermissionError):
        pathsec.open(str(target), "r")


# nltk.sem.util.read_sents
def test_read_sents_reads_inside_sandbox(sandbox):
    """Positive control: a legitimate read of a file inside the data sandbox
    still works and applies the normal blank-line / comment filtering."""
    from nltk.sem.util import read_sents

    good = sandbox.data_root / "sents.txt"
    good.write_text("hello\nworld\n# a comment\n\n")

    assert read_sents(str(good)) == ["hello", "world"]


def test_read_sents_refuses_outside(sandbox):
    """Attack: read_sents() of a path outside the sandbox must be refused, so a
    caller cannot use it to read /etc/passwd or any other out-of-root file."""
    from nltk.sem.util import read_sents

    target = sandbox.outside / "evil_sents.txt"
    target.write_text("secret\n")  # content is irrelevant; the read must fail

    with pytest.raises(PermissionError):
        read_sents(str(target))
