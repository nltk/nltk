"""Regression tests for decompression-bomb protection in NLTK (CWE-409).

NLTK reads whole zip members into memory (``ZipFilePathPointer.open`` /
``OpenOnDemandZipFile.read``) and extracts them to disk (``nltk.downloader``)
without any cap, so a tiny archive whose member decompresses to gigabytes
exhausts RAM or disk. ``nltk.data._check_decompression_bomb`` now rejects a
member that expands beyond ``MAX_UNZIP_RATIO`` (above an activation size) or past
the optional absolute cap ``MAX_UNZIP_SIZE``. Ordinary corpora compress only a
few-fold, so the guard does not affect legitimate data.
"""

import os
import zipfile

import pytest

import nltk.data as data
from nltk.data import ZipFilePathPointer
from nltk.downloader import ErrorMessage, _unzip_iter


@pytest.fixture(autouse=True)
def _restore_limits():
    """Snapshot and restore the configurable limits around each test."""
    saved = (data.MAX_UNZIP_RATIO, data.MAX_UNZIP_SIZE, data.MAX_UNZIP_ACTIVATION)
    yield
    data.MAX_UNZIP_RATIO, data.MAX_UNZIP_SIZE, data.MAX_UNZIP_ACTIVATION = saved


def _make_zip(path, member, payload):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member, payload)
    return path


def test_ratio_guard_blocks_bomb(tmp_path):
    """A member expanding past MAX_UNZIP_RATIO (above activation) is refused."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024  # 1 MiB
    data.MAX_UNZIP_RATIO = 100
    z = _make_zip(tmp_path / "bomb.zip", "m", b"\0" * (2 * 1024 * 1024))  # ~1000x
    with pytest.raises(ValueError, match="zip bomb"):
        ZipFilePathPointer(str(z), "m").open().read()


def test_low_ratio_member_passes(tmp_path):
    """Incompressible / low-ratio data is never rejected (no false positive)."""
    z = _make_zip(tmp_path / "ok.zip", "m", os.urandom(2 * 1024 * 1024))
    assert len(ZipFilePathPointer(str(z), "m").open().read()) == 2 * 1024 * 1024


def test_small_high_ratio_member_passes(tmp_path):
    """A small member below the activation size passes regardless of ratio."""
    # 1 MiB of zeros (huge ratio) but below the default 32 MiB activation.
    z = _make_zip(tmp_path / "small.zip", "m", b"\0" * (1024 * 1024))
    assert len(ZipFilePathPointer(str(z), "m").open().read()) == 1024 * 1024


def test_absolute_cap_blocks_oversize(tmp_path):
    """The optional MAX_UNZIP_SIZE hard cap refuses oversize members."""
    data.MAX_UNZIP_SIZE = 1024 * 1024  # 1 MiB
    z = _make_zip(tmp_path / "big.zip", "m", os.urandom(2 * 1024 * 1024))
    with pytest.raises(ValueError, match="MAX_UNZIP_SIZE"):
        ZipFilePathPointer(str(z), "m").open().read()


def test_downloader_extract_blocks_bomb(tmp_path):
    """The on-disk extraction path refuses a bomb member before writing it."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024  # 1 MiB
    data.MAX_UNZIP_RATIO = 100
    z = _make_zip(tmp_path / "pkg.zip", "pkg/big.txt", b"\0" * (2 * 1024 * 1024))
    dest = tmp_path / "out"
    messages = list(_unzip_iter(str(z), str(dest), verbose=False))
    assert any(isinstance(m, ErrorMessage) for m in messages), messages
    # nothing was written to disk
    assert not (dest / "pkg" / "big.txt").exists()


def test_downloader_writes_nothing_when_a_later_member_is_a_bomb(tmp_path):
    """A bomb after benign members must be caught before *anything* is written
    (validate-then-extract contract)."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024  # 1 MiB
    data.MAX_UNZIP_RATIO = 100
    zp = tmp_path / "pkg.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pkg/safe.txt", b"hello")  # benign member, comes first
        zf.writestr("pkg/big.txt", b"\0" * (2 * 1024 * 1024))  # bomb, comes later
    dest = tmp_path / "out"
    messages = list(_unzip_iter(str(zp), str(dest), verbose=False))
    assert any(isinstance(m, ErrorMessage) for m in messages), messages
    # neither the benign member nor the bomb was written
    assert not (dest / "pkg" / "safe.txt").exists()
    assert not (dest / "pkg" / "big.txt").exists()
