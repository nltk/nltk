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
import io
import os
import subprocess
import sys
import zipfile  # for the ZIP_DEFLATED constant only; opens go through pathsec

import pytest

import nltk.data as data
from nltk.data import GzipFileSystemPathPointer, ZipFilePathPointer
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
    with SecureZipFile(str(z)) as zf:
        data._check_decompression_bomb(zf.getinfo("bomb.gz"))
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
    p = _write_gz(tmp_path / "bomb.gz", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="gzip bomb"):
        GzipFileSystemPathPointer(str(p)).open().read()


def test_standalone_gzip_legit_passes(tmp_path):
    """A legit low-ratio standalone .gz still decompresses fully and correctly."""
    payload = b"corpus sentence.\n" * 100000
    p = _write_gz(tmp_path / "ok.gz", payload)
    assert GzipFileSystemPathPointer(str(p)).open().read() == payload


def test_standalone_gzip_absolute_cap(tmp_path):
    """MAX_UNZIP_SIZE also caps the standalone .gz layer's output."""
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
        with SecureZipFile(str(z)) as zf:
            zf.read("m")


def test_pathsec_zipfile_open_bomb_blocked(tmp_path):
    """pathsec.ZipFile.open() (streaming member) is bounded by the declared size."""
    z = _make_zip(tmp_path / "b.zip", "m", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="zip bomb"):
        with SecureZipFile(str(z)) as zf:
            zf.open("m")


@pytest.mark.parametrize("how", ["read", "readline", "iter"])
def test_pathsec_bounded_zip_ext_file_caps_actual_bytes(tmp_path, how):
    """open()'s declared-size pre-check catches honest bombs, but the returned
    streaming reader is the defense-in-depth backstop: it caps the ACTUAL
    decompressed bytes on every read path even if the declared size understated
    them. Drive _BoundedZipExtFile directly with a deliberately tiny compress_size
    (the pre-check bypassed) and confirm read()/readline()/iteration each trip
    (the reviewer's ask: preserve streaming semantics yet stay bounded, CWE-409)."""
    from nltk.data import _reject_decompression_total
    from nltk.pathsec import _BoundedZipExtFile

    data.MAX_UNZIP_ACTIVATION = 1024 * 1024
    data.MAX_UNZIP_RATIO = 10
    z = _make_zip(tmp_path / "m.zip", "m", b"\0" * (4 * 1024 * 1024))
    with SecureZipFile(str(z)) as zf:
        # zipfile.ZipFile.open bypasses our bounded override to hand back the raw
        # streaming ZipExtFile; wrap it with an UNDERSTATED compress_size so only the
        # actual-byte cap (not the ratio-vs-declared pre-check) can stop it.
        raw = zipfile.ZipFile.open(zf, "m")
        stream = io.BufferedReader(
            _BoundedZipExtFile(raw, 1024, "m", _reject_decompression_total)
        )
        with pytest.raises(ValueError, match="zip bomb"):
            if how == "read":
                stream.read()
            elif how == "readline":
                stream.readline()
            else:
                for _ in stream:
                    pass


def test_pathsec_zipfile_open_prefix_read_is_not_falsely_rejected(tmp_path):
    """Reading only a prefix of a large legit member must NOT trip the cap (proves
    streaming really streams instead of materialising the whole member)."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024
    data.MAX_UNZIP_RATIO = 10
    payload = os.urandom(8 * 1024 * 1024)  # incompressible, low ratio
    z = _make_zip(tmp_path / "big.zip", "m", payload)
    with SecureZipFile(str(z)) as zf:
        with zf.open("m") as stream:
            assert stream.read(4096) == payload[:4096]


def test_pathsec_zipfile_legit_read_passes(tmp_path):
    """A legit member still reads correctly through pathsec.ZipFile."""
    payload = b"hello world\n" * 500
    z = _make_zip(tmp_path / "ok.zip", "m", payload)
    with SecureZipFile(str(z)) as zf:
        assert zf.read("m") == payload
        assert zf.open("m").read() == payload
        # readline / iteration on a legit member behave normally
    with SecureZipFile(str(z)) as zf:
        assert zf.open("m").readline() == b"hello world\n"


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
        with SecureZipFile(str(z)) as zf:
            zf.extract("m", str(dest))
    assert not (dest / "m").exists() or (dest / "m").stat().st_size < 2 * 1024 * 1024


def test_pathsec_zipfile_extractall_bomb_blocked(tmp_path):
    z = _make_zip(tmp_path / "b.zip", "m", b"\0" * (64 * 1024 * 1024))
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ValueError, match="zip bomb"):
        with SecureZipFile(str(z)) as zf:
            zf.extractall(str(dest))


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
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024  # 1 MiB
    data.MAX_UNZIP_RATIO = 1000
    payload = os.urandom(2 * 1024 * 1024)  # incompressible: ratio ~1x, above activation
    p = _write_gz(tmp_path / "big.gz", payload)
    assert GzipFileSystemPathPointer(str(p)).open().read() == payload


# --- GzipFileSystemPathPointer now STREAMS (no whole-file buffering); the guard
#     must survive seeks, which decompress-and-discard OUTSIDE read() (CWE-409) -----
def test_gzip_pointer_seek_to_end_bomb_blocked(tmp_path):
    """seek(0, SEEK_END) makes GzipFile decompress the whole stream inside its own
    buffer (never through read()); the seek() guard must still refuse the bomb."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024
    data.MAX_UNZIP_RATIO = 10
    p = _write_gz(tmp_path / "bomb.gz", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="gzip bomb"):
        with GzipFileSystemPathPointer(str(p)).open() as s:
            s.seek(0, os.SEEK_END)


def test_gzip_pointer_forward_seek_past_ratio_blocked(tmp_path):
    """A forward absolute seek past the ratio threshold decompresses-and-discards up
    to that offset; the guard refuses once the offset breaches the policy."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024
    data.MAX_UNZIP_RATIO = 10
    p = _write_gz(tmp_path / "bomb.gz", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="gzip bomb"):
        with GzipFileSystemPathPointer(str(p)).open() as s:
            s.seek(60 * 1024 * 1024, os.SEEK_SET)


def test_gzip_pointer_seek_roundtrip_legit_passes(tmp_path):
    """seek(END) to size, seek(0), then a full read of a legit .gz must NOT be
    falsely rejected: the guard tracks the max offset reached, not summed reads."""
    payload = os.urandom(2 * 1024 * 1024)
    p = _write_gz(tmp_path / "ok.gz", payload)
    with GzipFileSystemPathPointer(str(p)).open() as s:
        assert s.seek(0, os.SEEK_END) == len(payload)
        s.seek(0)
        assert s.read() == payload
        # chunked reread after the seeks: still fine
        s.seek(0)
        acc = b""
        while True:
            chunk = s.read(65536)
            if not chunk:
                break
            acc += chunk
        assert acc == payload


def test_gzip_pointer_prefix_read_does_not_buffer_whole_file(tmp_path):
    """Reading only a prefix of a large legit .gz must succeed without tripping the
    cap, proving the pointer streams instead of materialising the whole payload."""
    data.MAX_UNZIP_ACTIVATION = 1024 * 1024
    data.MAX_UNZIP_RATIO = 10
    payload = os.urandom(8 * 1024 * 1024)  # incompressible, low ratio
    p = _write_gz(tmp_path / "big.gz", payload)
    with GzipFileSystemPathPointer(str(p)).open() as s:
        assert s.read(4096) == payload[:4096]


def test_gzip_pointer_compress_size_stat_is_cached(tmp_path):
    """_BoundedGzipFile stats the compressed size once and caches it: re-stat-ing on
    every read() is hot for chunked/line iteration (reviewer perf note)."""
    payload = os.urandom(4 * 1024 * 1024)
    p = _write_gz(tmp_path / "ok.gz", payload)
    calls = {"n": 0}
    real_getsize = os.path.getsize

    def counting_getsize(path):
        calls["n"] += 1
        return real_getsize(path)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("nltk.data.os.path.getsize", counting_getsize)
    try:
        with GzipFileSystemPathPointer(str(p)).open() as s:
            while s.read(65536):
                pass
    finally:
        monkeypatch.undo()
    assert calls["n"] == 1, f"compress_size stat not cached: {calls['n']} calls"


def test_gzip_pointer_with_encoding_streams_and_blocks(tmp_path):
    """The encoding path wraps the stream in SeekableUnicodeStreamReader (which seeks
    heavily): a legit text .gz decodes correctly and a bomb is still refused."""
    text = "corpus line éè\n" * 5000  # multibyte to exercise seek realignment
    p = _write_gz(tmp_path / "text.gz", text.encode("utf-8"))
    with GzipFileSystemPathPointer(str(p)).open(encoding="utf-8") as reader:
        assert reader.readline() == "corpus line éè\n"

    data.MAX_UNZIP_ACTIVATION = 1024 * 1024
    data.MAX_UNZIP_RATIO = 10
    pb = _write_gz(tmp_path / "bomb.gz", b"\0" * (64 * 1024 * 1024))
    with pytest.raises(ValueError, match="gzip bomb"):
        GzipFileSystemPathPointer(str(pb)).open(encoding="utf-8").read()


def test_pathsec_data_import_order_has_no_cycle():
    """pathsec.ZipFile's decompression guards are imported lazily to break the
    nltk.data <-> nltk.pathsec cycle; importing either module first must work.

    The child interpreter is given this process's import path so it can locate
    nltk exactly where the running tests found it (editable checkout, installed
    site-packages, or a PYTHONPATH override) rather than relying on its own cwd.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
    for first in ("nltk.pathsec", "nltk.data"):
        r = subprocess.run(
            [sys.executable, "-c", f"import {first}; import nltk.pathsec, nltk.data"],
            capture_output=True,
            env=env,
        )
        assert r.returncode == 0, r.stderr.decode()
