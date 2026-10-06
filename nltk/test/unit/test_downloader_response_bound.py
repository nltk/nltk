# Natural Language Toolkit: downloader response-bound tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""A hostile or misconfigured server could stream an unbounded response body and
exhaust the disk before the post-download integrity check runs (CWE-400).
_download_package bounds the read at the manifest-declared size plus a small
slack. Only the network reader is a double here (a real hostile server cannot be
stood up in a unit test); the read loop, the byte cap, the real on-disk write and
the cleanup all run for real."""

import hashlib
import os
import unittest.mock

from nltk.downloader import Downloader, ErrorMessage

_CHUNK = b"A" * (1024 * 16)
# What an uncapped loop would drain from a hostile server. The cap must stop us
# far below this.
_HARD_STOP = 8 * 1024 * 1024


class _StreamingReader:
    """Stands in for a hostile server: keeps yielding 16k chunks."""

    def __init__(self):
        self.served = 0

    def read(self, n=-1):
        if self.served >= _HARD_STOP:
            return b""  # safety net; reaching this means the cap FAILED
        self.served += len(_CHUNK)
        return _CHUNK

    def close(self):
        pass


class _Info:
    id = "dummy"
    url = "https://hostile.example/dummy.zip"
    size = 100  # the manifest claims a tiny file
    filename = os.path.join("corpora", "dummy.zip")
    subdir = "corpora"
    unzip = False
    sha256_checksum = hashlib.sha256(b"x").hexdigest()
    checksum = hashlib.md5(b"x").hexdigest()


def test_download_aborts_on_oversize_response(tmp_path):
    download_dir = str(tmp_path / "dl")
    os.makedirs(os.path.join(download_dir, "corpora"), exist_ok=True)
    downloader = Downloader(download_dir=download_dir)
    info = _Info()
    reader = _StreamingReader()

    with unittest.mock.patch(
        "nltk.downloader.urlopen", return_value=reader
    ), unittest.mock.patch.object(
        Downloader, "status", return_value=Downloader.NOT_INSTALLED
    ):
        messages = list(downloader._download_package(info, download_dir, force=True))

    # The cap held: we read nowhere near the 8 MB a hostile server would stream,
    # only the declared size plus the ~1 MB slack (and the chunk that tripped it).
    assert reader.served <= info.size + 1024 * 1024 + 2 * len(_CHUNK), reader.served
    assert reader.served < _HARD_STOP

    # The oversize download was rejected, not committed.
    assert any(isinstance(m, ErrorMessage) for m in messages), messages

    # Neither the temp file nor the final destination survives.
    final = os.path.join(download_dir, info.filename)
    assert not os.path.exists(final)
    assert not os.path.exists(final + ".tmp")


def test_exact_size_response_is_accepted_up_to_integrity_check(tmp_path):
    # A well-behaved server that sends exactly info.size bytes is NOT tripped by
    # the cap (it fails later only on the checksum, proving the cap is not the
    # thing rejecting an in-bound body).
    download_dir = str(tmp_path / "dl2")
    os.makedirs(os.path.join(download_dir, "corpora"), exist_ok=True)
    downloader = Downloader(download_dir=download_dir)

    class _Exact(_Info):
        size = len(_CHUNK)  # one chunk, well under the 1 MB slack

    served = {"done": False}

    class _OneChunk:
        def read(self, n=-1):
            if served["done"]:
                return b""
            served["done"] = True
            return _CHUNK

        def close(self):
            pass

    with unittest.mock.patch(
        "nltk.downloader.urlopen", return_value=_OneChunk()
    ), unittest.mock.patch.object(
        Downloader, "status", return_value=Downloader.NOT_INSTALLED
    ):
        messages = list(
            downloader._download_package(_Exact(), download_dir, force=True)
        )

    # It read the whole (in-bound) body; any rejection is from the checksum, not
    # the size cap.
    assert any(isinstance(m, ErrorMessage) for m in messages)
