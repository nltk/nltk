# Natural Language Toolkit: aggregate decompression-bomb guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""A zip whose members SUM to a bomb must be refused, not only per-member.

_check_decompression_bomb runs per member and only ratio-checks a member above
32 MiB (MAX_UNZIP_ACTIVATION). So an archive of many members each just under the
floor is never individually refused, yet the members together expand from a tiny
zip to an arbitrarily large total, and extraction kept no running byte total.
_check_zip_total_size applies the same activation-plus-ratio test at the whole
archive level.
"""

import os
import shutil
import tempfile
import zipfile

import pytest

import nltk.data
from nltk import pathsec


@pytest.fixture
def sandbox_root(monkeypatch):
    root = tempfile.mkdtemp(prefix="nltk_sandbox_root_")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_members_below_the_floor_that_aggregate_to_a_bomb_are_refused(sandbox_root):
    """Each member is below MAX_UNZIP_ACTIVATION so the per-member guard passes;
    together they are a ratio-1000+ bomb."""
    archive = os.path.join(sandbox_root, "bomb.zip")
    zeros = b"\0" * (20 * 1024 * 1024)  # 20 MiB, below the 32 MiB floor
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for index in range(20):  # 400 MiB total from a sub-MB zip
            handle.writestr(f"z{index}.dat", zeros)

    # Confirm the per-member guard alone would NOT catch these.
    from nltk.data import _check_decompression_bomb

    for info in zipfile.ZipFile(archive).infolist():
        _check_decompression_bomb(info)  # must not raise

    with pytest.raises((PermissionError, ValueError)):
        with pathsec.ZipFile(archive):
            pass


def test_a_small_legitimate_zip_is_allowed(sandbox_root):
    archive = os.path.join(sandbox_root, "ok.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("a.txt", "hello")
        handle.writestr("b/c.txt", "world")
    with pathsec.ZipFile(archive) as handle:
        assert handle.namelist() == ["a.txt", "b/c.txt"]


def test_a_large_but_honest_corpus_is_allowed(sandbox_root):
    """A real corpus is large but has a modest overall ratio, so it must pass:
    the guard refuses bombs, not size."""
    archive = os.path.join(sandbox_root, "big.zip")
    incompressible = os.urandom(1024 * 1024)  # ratio ~1
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for index in range(60):  # ~60 MiB, ratio ~1
            handle.writestr(f"f{index}", incompressible)
    with pathsec.ZipFile(archive) as handle:
        assert len(handle.namelist()) == 60


def test_a_moderate_ratio_archive_below_the_threshold_is_allowed(sandbox_root):
    """Ratio ~500 is under MAX_UNZIP_RATIO=1000, so it is not a bomb even though
    it compresses well. Pins that the aggregate check uses the same threshold."""
    archive = os.path.join(sandbox_root, "mid.zip")
    block = b"NLTKPADDINGBLOCK" * 128  # ~500:1 compressible
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for index in range(40):
            handle.writestr(f"m{index}.dat", block * 2560)
    with pathsec.ZipFile(archive) as handle:
        assert len(handle.namelist()) == 40
