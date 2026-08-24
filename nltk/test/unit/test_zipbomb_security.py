"""Regression tests for decompression-bomb protection in NLTK (CWE-409).

NLTK reads whole zip members into memory (``ZipFilePathPointer.open`` /
``OpenOnDemandZipFile.read``) and extracts them to disk (``nltk.downloader``)
without any cap, so a tiny archive whose member decompresses to gigabytes
exhausts RAM or disk. ``nltk.data._check_decompression_bomb`` now rejects a
member that expands beyond ``MAX_UNZIP_RATIO`` (above an activation size) or past
the optional absolute cap ``MAX_UNZIP_SIZE``. Ordinary corpora compress only a
few-fold, so the guard does not affect legitimate data.

The gzip layers are bounded too (``_bounded_gzip_decompress``): a ``.gz`` member
inside a zip (``ZipFilePathPointer.open``) and a standalone ``.gz`` on disk
(``GzipFileSystemPathPointer.open``) are second decompression layers the zip
member-size guard never sees, so each is streamed under the same policy.
"""

import gzip
import os
import zipfile  # for the ZIP_DEFLATED constant only; opens go through pathsec

import pytest

import nltk.data as data
from nltk.data import ZipFilePathPointer
from nltk.downloader import ErrorMessage, _unzip_iter
from nltk.pathsec import ZipFile as SecureZipFile
from nltk.pathsec import open as pathsec_open


@pytest.fixture(autouse=True)
def _restore_limits():
    """Snapshot and restore the configurable limits around each test."""
    saved = (data.MAX_UNZIP_RATIO, data.MAX_UNZIP_SIZE, data.MAX_UNZIP_ACTIVATION)
    yield
    data.MAX_UNZIP_RATIO, data.MAX_UNZIP_SIZE, data.MAX_UNZIP_ACTIVATION = saved


# These sandbox helpers use the pathsec-secured wrappers, never a bare open: the
# tmp_path fixtures live under an authorized data root (see conftest), so the whole
# harness dogfoods the hardened API. A bare open is used only where a test must
# create something *outside* the sandbox (none here).
def _secure_zip(path, members):
    with SecureZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in members.items():
            zf.writestr(name, payload)
    return path


def _make_zip(path, member, payload):
    return _secure_zip(path, {member: payload})


def _write_gz(path, payload):
    with pathsec_open(str(path), "wb", context="test_zipbomb") as f:
        f.write(gzip.compress(payload))
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
    zp = _secure_zip(
        tmp_path / "pkg.zip",
        {"pkg/safe.txt": b"hello", "pkg/big.txt": b"\0" * (2 * 1024 * 1024)},
    )
    dest = tmp_path / "out"
    messages = list(_unzip_iter(str(zp), str(dest), verbose=False))
    assert any(isinstance(m, ErrorMessage) for m in messages), messages
    # neither the benign member nor the bomb was written
    assert not (dest / "pkg" / "safe.txt").exists()
    assert not (dest / "pkg" / "big.txt").exists()


# --- nested gzip inside a zip member (the .gz second decompression layer) ------


def test_nested_gzip_bomb_blocked(tmp_path):
    """A .gz zip member whose (tiny) gz bytes pass the member guard but whose gzip
    layer expands past the ratio is refused (nested-gzip bomb, CWE-409)."""
    data.MAX_UNZIP_ACTIVATION = 64 * 1024
    data.MAX_UNZIP_RATIO = 10
    gz = gzip.compress(b"\0" * (256 * 1024))
    z = _make_zip(tmp_path / "nested.zip", "bomb.gz", gz)
    # the zip member itself passes the guard (its declared sizes are tiny)
    data._check_decompression_bomb(SecureZipFile(str(z)).getinfo("bomb.gz"))
    with pytest.raises(ValueError, match="gzip bomb"):
        ZipFilePathPointer(str(z), "bomb.gz").open().read()


def test_nested_gzip_forged_isize_caught_by_streaming_cap(tmp_path):
    """Even with a forged gzip ISIZE trailer (claims 0 bytes), the streaming cap
    still refuses the bomb; the ISIZE pre-check is only an optimization."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024
    data.MAX_UNZIP_RATIO = 10
    gz = bytearray(gzip.compress(b"\0" * (4 * 1024 * 1024)))
    gz[-4:] = (0).to_bytes(4, "little")  # lie about the uncompressed size
    z = _make_zip(tmp_path / "forged.zip", "bomb.gz", bytes(gz))
    with pytest.raises(ValueError, match="gzip bomb"):
        ZipFilePathPointer(str(z), "bomb.gz").open().read()


def test_nested_gzip_absolute_cap(tmp_path):
    """MAX_UNZIP_SIZE also caps the nested gzip layer's output."""
    data.MAX_UNZIP_SIZE = 64 * 1024
    gz = gzip.compress(b"\0" * (256 * 1024))
    z = _make_zip(tmp_path / "cap.zip", "big.gz", gz)
    with pytest.raises(ValueError, match="MAX_UNZIP_SIZE"):
        ZipFilePathPointer(str(z), "big.gz").open().read()


def test_nested_gzip_legit_member_passes(tmp_path):
    """A legitimate .gz member (low ratio) still decompresses to its content."""
    payload = b"legitimate corpus line\n" * 64
    z = _make_zip(tmp_path / "ok.zip", "data.gz", gzip.compress(payload))
    assert ZipFilePathPointer(str(z), "data.gz").open().read() == payload


def test_nested_gzip_ratio_cap_is_load_bearing(tmp_path):
    """Mutation test: with the activation/ratio cap tuned to catch it the nested
    gzip bomb is refused; raise the activation threshold above the output and the
    SAME payload decompresses, proving the cap (not another check) is the guard
    that stops the second decompression layer (CWE-409)."""
    gz = gzip.compress(b"\0" * (256 * 1024))
    z = _make_zip(tmp_path / "mut.zip", "bomb.gz", gz)

    data.MAX_UNZIP_ACTIVATION = 64 * 1024
    data.MAX_UNZIP_RATIO = 10
    data.MAX_UNZIP_SIZE = None
    with pytest.raises(ValueError, match="gzip bomb"):
        ZipFilePathPointer(str(z), "bomb.gz").open().read()

    # neuter the cap: activation above the 256 KiB output -> no longer refused
    data.MAX_UNZIP_ACTIVATION = 1 << 30
    out = ZipFilePathPointer(str(z), "bomb.gz").open().read()
    assert len(out) == 256 * 1024


# --- standalone .gz file (GzipFileSystemPathPointer, not inside a zip) ----------
def test_standalone_gzip_bomb_blocked(tmp_path):
    """A standalone .gz on disk read via GzipFileSystemPathPointer is bounded by
    the same policy, so it cannot exhaust memory (CWE-409)."""
    from nltk.data import GzipFileSystemPathPointer

    p = _write_gz(tmp_path / "bomb.gz", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="gzip bomb"):
        GzipFileSystemPathPointer(str(p)).open().read()


def test_standalone_gzip_legit_passes(tmp_path):
    """A legit low-ratio standalone .gz still decompresses fully and correctly."""
    from nltk.data import GzipFileSystemPathPointer

    payload = b"corpus sentence.\n" * 100000
    p = _write_gz(tmp_path / "ok.gz", payload)
    assert GzipFileSystemPathPointer(str(p)).open().read() == payload


def test_standalone_gzip_absolute_cap(tmp_path):
    """MAX_UNZIP_SIZE also caps the standalone .gz layer's output."""
    from nltk.data import GzipFileSystemPathPointer

    data.MAX_UNZIP_SIZE = 1024
    p = _write_gz(tmp_path / "big.gz", b"x" * 4096)
    with pytest.raises(ValueError, match="MAX_UNZIP_SIZE"):
        GzipFileSystemPathPointer(str(p)).open().read()


# --- pathsec.ZipFile.read/open: the "secure" wrapper must bound decompression ---
def test_pathsec_zipfile_read_bomb_blocked(tmp_path):
    """pathsec.ZipFile.read() decompresses a whole member; it must be capped so the
    secure wrapper cannot be used as a bomb (CWE-409)."""
    z = _make_zip(tmp_path / "b.zip", "m", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="zip bomb"):
        SecureZipFile(str(z)).read("m")


def test_pathsec_zipfile_open_bomb_blocked(tmp_path):
    """pathsec.ZipFile.open() (streaming member) is bounded by the declared size."""
    z = _make_zip(tmp_path / "b.zip", "m", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="zip bomb"):
        SecureZipFile(str(z)).open("m")


def test_pathsec_zipfile_legit_read_passes(tmp_path):
    """A legit member still reads correctly through pathsec.ZipFile."""
    payload = b"hello world\n" * 500
    z = _make_zip(tmp_path / "ok.zip", "m", payload)
    assert SecureZipFile(str(z)).read("m") == payload
    assert SecureZipFile(str(z)).open("m").read() == payload


def test_weka_version_check_refuses_bomb_jar(tmp_path):
    """_check_weka_version opens the jar and reads weka/core/version.txt; a
    malicious jar declaring a gigabyte version.txt must not be read into RAM."""
    from nltk.classify.weka import _check_weka_version

    jar = _make_zip(
        tmp_path / "weka.jar", "weka/core/version.txt", b"\0" * (64 * 1024 * 1024)
    )
    with pytest.raises(ValueError, match="zip bomb"):
        _check_weka_version(str(jar))


# --- the remaining entry points: OpenOnDemandZipFile, extract/extractall,
#     nltk.data.find end-to-end, and the deprecated BufferedGzipFile -------------
def test_open_on_demand_zipfile_read_bomb_blocked(tmp_path):
    from nltk.data import OpenOnDemandZipFile

    z = _make_zip(tmp_path / "b.zip", "m", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="zip bomb"):
        OpenOnDemandZipFile(str(z)).read("m")


def test_pathsec_zipfile_extract_bomb_blocked(tmp_path):
    """extract() decompresses to disk via self.open(); the bounded open() stops it."""
    z = _make_zip(tmp_path / "b.zip", "m", b"\0" * (64 * 1024 * 1024))
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ValueError, match="zip bomb"):
        SecureZipFile(str(z)).extract("m", str(dest))
    assert not (dest / "m").exists() or (dest / "m").stat().st_size < 2 * 1024 * 1024


def test_pathsec_zipfile_extractall_bomb_blocked(tmp_path):
    z = _make_zip(tmp_path / "b.zip", "m", b"\0" * (64 * 1024 * 1024))
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ValueError, match="zip bomb"):
        SecureZipFile(str(z)).extractall(str(dest))


def test_nltk_data_find_gz_bomb_blocked_end_to_end(tmp_path, monkeypatch):
    """nltk.data.find(name).open().read() on a standalone .gz bomb is refused."""
    _write_gz(tmp_path / "payload.gz", b"\0" * (64 * 1024 * 1024))
    monkeypatch.setattr(data, "path", [str(tmp_path)])
    with pytest.raises(ValueError, match="gzip bomb"):
        data.find("payload.gz").open().read()


def test_buffered_gzip_file_bomb_blocked(tmp_path):
    """The deprecated BufferedGzipFile.read() is bounded too (CWE-409)."""
    from nltk.data import BufferedGzipFile

    p = _write_gz(tmp_path / "b.gz", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="gzip bomb"):
        BufferedGzipFile(str(p)).read()


def test_buffered_gzip_file_legit_passes(tmp_path):
    from nltk.data import BufferedGzipFile

    payload = b"corpus sentence.\n" * 1000
    p = _write_gz(tmp_path / "ok.gz", payload)
    assert BufferedGzipFile(str(p)).read() == payload


# --- gzip_open_unicode (the last raw-GzipFile read path) + misc coverage --------
def test_gzip_open_unicode_read_bomb_blocked(tmp_path):
    from nltk.data import gzip_open_unicode

    p = _write_gz(tmp_path / "b.gz", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="gzip bomb"):
        gzip_open_unicode(str(p), "rb").read()


def test_gzip_open_unicode_write_read_roundtrip(tmp_path):
    """The write path (used by maxent) still works and reads back correctly."""
    from nltk.data import gzip_open_unicode

    text = "corpus line\n" * 200
    p = tmp_path / "w.gz"
    with gzip_open_unicode(str(p), "w") as f:
        f.write(text)
    assert gzip_open_unicode(str(p), "rb").read() == text


def test_buffered_gzip_file_chunked_bomb_blocked(tmp_path):
    """Reading the bomb in fixed chunks is caught on cumulative bytes, not just a
    single whole-file read()."""
    from nltk.data import BufferedGzipFile

    p = _write_gz(tmp_path / "b.gz", b"\0" * (64 * 1024 * 1024))
    f = BufferedGzipFile(str(p))
    with pytest.raises(ValueError, match="gzip bomb"):
        while True:
            if not f.read(1 << 20):
                break


def test_gzip_low_ratio_above_activation_passes(tmp_path):
    """A large .gz crossing the activation floor but low-ratio (like a real language
    model) still decompresses fully -- no false positive."""
    from nltk.data import GzipFileSystemPathPointer

    data.MAX_UNZIP_ACTIVATION = 1024 * 1024  # 1 MiB
    data.MAX_UNZIP_RATIO = 1000
    payload = os.urandom(2 * 1024 * 1024)  # incompressible: ratio ~1x, above activation
    p = _write_gz(tmp_path / "big.gz", payload)
    assert GzipFileSystemPathPointer(str(p)).open().read() == payload


def test_pathsec_data_import_order_has_no_cycle():
    """pathsec.ZipFile's decompression guards are imported lazily to break the
    nltk.data <-> nltk.pathsec cycle; importing either module first must work."""
    import subprocess
    import sys

    for first in ("nltk.pathsec", "nltk.data"):
        r = subprocess.run(
            [sys.executable, "-c", f"import {first}; import nltk.pathsec, nltk.data"],
            capture_output=True,
        )
        assert r.returncode == 0, r.stderr.decode()
