# Natural Language Toolkit: downloader URL-scheme attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""End-to-end pins for the downloader's package URL (found by the line sweep
of every ``urlopen``): a poisoned index entry, or a package host that
redirects, must not turn ``Downloader._download_package`` into a local file
reader (CWE-73 / CWE-918). The pathsec unit tests pin ``validate_network_url``
itself; these drive the real download path and check that nothing lands in
the data directory. The one permitted ``file://`` form, a package mirrored
inside a data root, stays working.

The outside target lives under ``$HOME``: the private per-user temp root is a
trusted pathsec root on macOS, so a temp dir would be a false "outside". File
URLs are built with ``Path.as_uri()`` so they are well formed on Windows too
(``file:///C:/...``, never the drive letter followed by a backslash path)."""

import hashlib
import http.server
import os
import shutil
import socketserver
import tempfile
import threading
from pathlib import Path

import pytest

import nltk.downloader as downloader
import nltk.pathsec as pathsec

_BODY = b"s3cret\n"


def _package(url):
    return downloader.Package(
        id="evil",
        url=url,
        name="evil",
        subdir="corpora",
        checksum=hashlib.md5(_BODY).hexdigest(),
        sha256_checksum=hashlib.sha256(_BODY).hexdigest(),
        size=len(_BODY),
        unzipped_size=len(_BODY),
        filename="evil.txt",
    )


@pytest.fixture
def dirs(monkeypatch):
    home = Path.home()
    root = Path(tempfile.mkdtemp(prefix=".nltk_dl_root_", dir=home))
    outside = Path(tempfile.mkdtemp(prefix=".nltk_dl_out_", dir=home))
    import nltk

    monkeypatch.setattr(nltk.data, "path", [str(root)] + list(nltk.data.path))
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    (outside / "secret.txt").write_bytes(_BODY)
    try:
        yield root, outside
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


def _run(root, url):
    errors = []
    try:
        for message in downloader.Downloader(download_dir=str(root))._download_package(
            _package(url), str(root), force=True
        ):
            if isinstance(message, downloader.ErrorMessage):
                errors.append(str(message.message))
    except Exception as exc:
        errors.append(repr(exc))
    return errors, (root / "corpora" / "evil.txt").exists()


def test_negative_control_outside_is_really_outside(dirs):
    root, outside = dirs
    with pytest.raises(PermissionError):
        pathsec.open(str(outside / "secret.txt"), "rb")


def test_file_url_outside_root_is_not_read(dirs):
    root, outside = dirs
    errors, written = _run(root, (outside / "secret.txt").as_uri())
    assert not written
    assert errors and "Security Violation" in errors[0]


@pytest.mark.parametrize(
    "url", ["file:///dev/zero", "ftp://127.0.0.1/x", "data:text/plain,hi"]
)
def test_non_http_schemes_and_devices_refused(dirs, url):
    root, _ = dirs
    errors, written = _run(root, url)
    assert not written and errors


def test_http_redirect_to_file_url_is_refused(dirs):
    root, outside = dirs
    target = (outside / "secret.txt").as_uri()

    class Redirect(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Redirect)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        errors, written = _run(root, f"http://127.0.0.1:{port}/evil.txt")
    finally:
        server.shutdown()
        server.server_close()
    assert not written
    assert errors and "Security Violation" in errors[0]


def test_file_url_inside_root_mirror_still_works(dirs):
    root, _ = dirs
    mirror = root / "mirror.txt"
    mirror.write_bytes(_BODY)
    errors, written = _run(root, mirror.as_uri())
    assert written and not errors
    assert (root / "corpora" / "evil.txt").read_bytes() == _BODY
