"""Regression tests for symlink-following arbitrary file write in the downloader (CWE-59).

``Downloader._download_package`` writes the package body to
``os.path.join(download_dir, info.filename)`` (``info.filename`` is taken from
the package index and is attacker-controllable).  A containment check guards
against ``../`` traversal, but a purely *lexical* check is bypassed by a symlink
that already exists *inside* ``download_dir`` and points outside it: the target
is lexically contained, yet ``open()`` / ``os.replace()`` follow the link and
write outside the download directory.

The check must therefore be symlink-aware: it resolves the deepest existing
ancestor of the real write targets before comparing, so a planted symlink cannot
redirect the write out of ``download_dir``.  These tests pin that behaviour and
also assert that legitimate downloads (including into a download dir that is
itself a symlink) keep working.
"""

import hashlib
import io
import os
import tempfile

import pytest

from nltk.downloader import Downloader, ErrorMessage, Package


def _can_symlink():
    # os.symlink exists on Windows but raises OSError/NotImplementedError without
    # Developer Mode/admin (or where symlinks are disabled); skip rather than fail.
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        dst = os.path.join(d, "dst")
        open(src, "w").close()
        try:
            os.symlink(src, dst)
            return True
        except (OSError, NotImplementedError, AttributeError):
            return False


pytestmark = pytest.mark.skipif(
    not _can_symlink(), reason="symlinks not supported on this platform/environment"
)

PAYLOAD = b"package-body-bytes\n"


def _package(filename, **overrides):
    # Extract extension from the intended filename to build a matching URL,
    # ensuring Package.__init__ reconstructs the base filename correctly.
    ext = os.path.splitext(filename)[1]
    attrib = dict(
        id="p",
        name="p",
        subdir="corpora",
        url=f"http://example.invalid/p{ext}",
        size=str(len(PAYLOAD)),
        unzipped_size="0",
        checksum="0",
        sha256_checksum=hashlib.sha256(PAYLOAD).hexdigest(),
        unzip="0",
        filename=filename,
    )
    attrib.update(overrides)
    return Package(**attrib)


class _FakeResp(io.BytesIO):
    def close(self):  # urlopen handle is closed by the downloader
        pass


@pytest.fixture
def fake_urlopen(monkeypatch):
    monkeypatch.setattr(
        "nltk.downloader.urlopen", lambda url, *a, **k: _FakeResp(PAYLOAD)
    )


def _run(pkg, download_dir):
    dl = Downloader()
    return list(dl.incr_download(pkg, str(download_dir), force=True))


def test_symlink_inside_download_dir_cannot_redirect_write(tmp_path, fake_urlopen):
    """A symlink planted inside download_dir must not let the write escape it."""
    download_dir = tmp_path / "nltk_data"
    (download_dir / "corpora").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    # Attacker pre-plants download_dir/corpora/evil -> outside.
    os.symlink(outside, download_dir / "corpora" / "evil")

    pkg = _package("corpora/p.txt")
    # Manually re-inject the malicious path after initialization to test downloader containment
    pkg.filename = "corpora/evil/OWNED.txt"
    msgs = _run(pkg, download_dir)

    assert any(isinstance(m, ErrorMessage) for m in msgs)
    # Nothing written through the symlink, outside the download dir.
    assert not (outside / "OWNED.txt").exists()


def test_symlink_to_parent_of_download_dir_is_blocked(tmp_path, fake_urlopen):
    """A symlink inside download_dir pointing to an *ancestor* must be blocked.

    Regression for an early-return that used the resolved (not lexical) ancestor:
    a link resolving to a parent of download_dir would otherwise be treated as
    "at/above download_dir" and wrongly allowed.
    """
    download_dir = tmp_path / "nltk_data"
    (download_dir / "corpora").mkdir(parents=True)
    # download_dir/corpora/up -> tmp_path  (an ancestor of download_dir)
    os.symlink(tmp_path, download_dir / "corpora" / "up")

    pkg = _package("corpora/p.txt")
    # Manually re-inject the malicious path after initialization
    pkg.filename = "corpora/up/OWNED.txt"
    msgs = _run(pkg, download_dir)

    assert any(isinstance(m, ErrorMessage) for m in msgs)
    assert not (tmp_path / "OWNED.txt").exists()


def test_symlink_via_subdir_component_is_blocked(tmp_path, fake_urlopen):
    """subdir routing through a planted symlink is blocked too (no `..` needed)."""
    download_dir = tmp_path / "nltk_data"
    (download_dir / "corpora").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, download_dir / "corpora" / "link")

    # subdir validation only rejects `..`/absolute, not a symlink component.
    pkg = _package(filename="corpora/p.txt", subdir="corpora/link")
    # Manually re-inject the malicious path after initialization
    pkg.filename = "corpora/link/x"
    msgs = _run(pkg, download_dir)

    assert any(isinstance(m, ErrorMessage) for m in msgs)
    assert not (outside / "x").exists()


def test_symlink_at_tmp_leaf_is_blocked(tmp_path, fake_urlopen):
    """A symlink planted at the leaf `.tmp` target must not be followed."""
    download_dir = tmp_path / "nltk_data"
    (download_dir / "corpora").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret"
    # download writes filepath + ".tmp" first -> plant a symlink there.
    os.symlink(secret, download_dir / "corpora" / "p.zip.tmp")

    # This does not require manual injection since Package.__init__ correctly
    # derives "corpora/p.zip" which the downloader uses to append ".tmp".
    pkg = _package("corpora/p.zip")
    msgs = _run(pkg, download_dir)

    assert any(isinstance(m, ErrorMessage) for m in msgs)
    assert not secret.exists()


def test_legitimate_download_still_works(tmp_path, fake_urlopen):
    """A normal, contained package is written inside download_dir."""
    download_dir = tmp_path / "nltk_data"
    download_dir.mkdir()

    pkg = _package("corpora/p.txt")
    msgs = _run(pkg, download_dir)

    assert not any(isinstance(m, ErrorMessage) for m in msgs)
    assert (download_dir / "corpora" / "p.txt").read_bytes() == PAYLOAD


def test_legitimate_symlinked_download_dir_still_works(tmp_path, fake_urlopen):
    """A download_dir that is itself a symlink is allowed (resolves to itself)."""
    real = tmp_path / "real_data"
    real.mkdir()
    download_dir = tmp_path / "nltk_data"  # symlink -> real
    os.symlink(real, download_dir)

    pkg = _package("corpora/p.txt")
    msgs = _run(pkg, download_dir)

    assert not any(isinstance(m, ErrorMessage) for m in msgs)
    assert (real / "corpora" / "p.txt").read_bytes() == PAYLOAD
