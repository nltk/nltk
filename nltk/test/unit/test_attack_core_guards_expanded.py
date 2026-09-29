# Natural Language Toolkit: expanded attack harness for the downloader bounds,
# the decorator signature fence and the read_str literal boundary
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The downloader, decorators and internals guards driven with the widest
attack matrix, benign neighbours included, judged by what the sink would have
received. Only the downloader's network reader is stood in for (a hostile
server cannot run in a unit test); the guards and file writes run for real."""

import hashlib
import os
import time

import pytest

NUL = chr(0)


# === 1. Downloader: the declared size is capped, the index body is bounded ===
# A safety net above every bound under test (the 64 MiB index ceiling included):
# with a guard broken, the endless reader stops here, so the test fails on its
# served-bytes assertion instead of filling the disk.
_HARD_STOP = 128 * 1024 * 1024


class _Counting:
    """A server stand-in that records how much was asked of it."""

    def __init__(self, body=b"", endless=False):
        self.body, self.endless, self.served, self.reads = body, endless, 0, 0

    def read(self, n=-1):
        self.reads += 1
        if self.endless:
            if self.served >= _HARD_STOP:
                return b""  # reaching this means the guard under test FAILED
            chunk = b"<x>" * 1024
        else:
            chunk, self.body = self.body[:n], self.body[n:]
        self.served += len(chunk)
        return chunk

    def close(self):
        pass


class TestDownloaderCeilings:
    def _info(self, size):
        class _Info:
            id = "dummy"
            url = "https://hostile.example/dummy.zip"
            filename = os.path.join("corpora", "dummy.zip")
            subdir = "corpora"
            unzip = False
            sha256_checksum = hashlib.sha256(b"x").hexdigest()
            checksum = hashlib.md5(b"x").hexdigest()

        _Info.size = size
        return _Info()

    @pytest.mark.parametrize("size", [10**12, 2**40, 1024**3 + 1, -1, -(10**9)])
    def test_an_out_of_range_declared_size_fetches_nothing(self, tmp_path, size):
        import unittest.mock

        from nltk.downloader import Downloader, ErrorMessage

        download_dir = str(tmp_path / "dl")
        os.makedirs(os.path.join(download_dir, "corpora"))
        reader = _Counting(endless=True)
        with unittest.mock.patch(
            "nltk.downloader.urlopen", return_value=reader
        ) as opened, unittest.mock.patch.object(
            Downloader, "status", return_value=Downloader.NOT_INSTALLED
        ):
            messages = list(
                Downloader(download_dir=download_dir)._download_package(
                    self._info(size), download_dir, force=True
                )
            )
        assert opened.call_count == 0 and reader.reads == 0
        assert any(isinstance(m, ErrorMessage) for m in messages)
        assert not os.path.exists(
            os.path.join(download_dir, "corpora", "dummy.zip.tmp")
        )

    def test_the_ceiling_is_above_every_real_package(self):
        # the largest package in the real index is under 100 MB; the ceiling
        # is a DoS bound, not a business limit
        from nltk.downloader import MAX_PACKAGE_BYTES

        assert MAX_PACKAGE_BYTES >= 10 * 100 * 1024 * 1024

    def test_a_declared_size_inside_the_range_is_still_bounded_by_it(self, tmp_path):
        import unittest.mock

        from nltk.downloader import Downloader, ErrorMessage

        download_dir = str(tmp_path / "dl")
        os.makedirs(os.path.join(download_dir, "corpora"))
        reader = _Counting(endless=True)
        with unittest.mock.patch(
            "nltk.downloader.urlopen", return_value=reader
        ), unittest.mock.patch.object(
            Downloader, "status", return_value=Downloader.NOT_INSTALLED
        ):
            messages = list(
                Downloader(download_dir=download_dir)._download_package(
                    self._info(100), download_dir, force=True
                )
            )
        assert reader.served <= 100 + 1024 * 1024 + 2 * 16 * 1024
        assert any(isinstance(m, ErrorMessage) for m in messages)

    def test_an_endless_index_is_refused_not_read_whole(self, tmp_path):
        import unittest.mock

        from nltk.downloader import MAX_INDEX_BYTES, Downloader

        reader = _Counting(endless=True)
        downloader = Downloader(download_dir=str(tmp_path))
        with unittest.mock.patch("nltk.downloader.urlopen", return_value=reader):
            with pytest.raises(ValueError, match="larger than"):
                downloader._update_index(url="https://hostile.example/index.xml")
        assert reader.served <= MAX_INDEX_BYTES + 64 * 1024

    def test_a_real_sized_index_still_parses(self, tmp_path):
        import unittest.mock

        from nltk.downloader import Downloader

        body = (
            b'<?xml version="1.0"?><nltk_data><packages>'
            b'<package id="p" name="P" size="3" unzipped_size="3" url="https://x/p.zip" '
            b'checksum="d41d8cd98f00b204e9800998ecf8427e" subdir="corpora" unzip="1" />'
            b"</packages><collections/></nltk_data>"
        )
        downloader = Downloader(download_dir=str(tmp_path))
        with unittest.mock.patch(
            "nltk.downloader.urlopen", return_value=_Counting(body)
        ):
            downloader._update_index(url="https://example.invalid/index.xml")
        assert downloader.info("p").size == 3


# === 2. Decorators: the signature fence ===
class TestSignatureFence:
    def test_every_legal_name_passes_including_non_ascii(self):
        from nltk.decorators import _assert_safe_signature, decorator

        for sig in (
            "caf" + chr(0xE9),
            chr(0xDF) + ", x",
            "_",
            "x1, *a, **k",
            "a, *, b",
            "a, /, b",
            "",
            "  ",
        ):
            _assert_safe_signature(sig)

        def caller(func, *a, **k):
            return func(*a, **k)

        exec_locals = {}
        exec(  # bare-exec ok: builds a test function with a non-ASCII parameter
            "def f(caf" + chr(0xE9) + "=1):\n    return caf" + chr(0xE9), exec_locals
        )
        assert decorator(caller)(exec_locals["f"])(5) == 5

    @pytest.mark.parametrize(
        "sig",
        [
            "a b",
            "a, b): pass",
            "a\nb",
            "a\tb",
            "a=1",
            "a: int",
            "a.b",
            "a()",
            "a[0]",
            "__import__('os')",
            "lambda",
            "import",
            "None",
            "a, ,b",
            ",",
            "**",
            "***a",
            "* a",
            "/ a",
            "a" + NUL,
            "a" + chr(0x2028) + "b",
            "a, b, " + "x, " * 5000 + "!",
        ],
        ids=lambda s: repr(s)[:16],
    )
    def test_everything_that_is_not_a_name_list_is_refused(self, sig):
        from nltk.decorators import _assert_safe_signature

        started = time.perf_counter()
        with pytest.raises(ValueError, match="non-identifier signature"):
            _assert_safe_signature(sig)
        assert time.perf_counter() - started < 1.0

    def test_a_non_string_signature_is_refused(self):
        from nltk.decorators import _assert_safe_signature

        for value in (None, 1, ["a"], b"a"):
            with pytest.raises(ValueError):
                _assert_safe_signature(value)

    def test_the_fence_is_load_bearing(self, tmp_path):
        # a crafted signature carries a default expression; with the fence
        # removed the eval runs it (the marker file appears), with the fence in
        # place the refusal happens before any code is built
        from nltk import decorators

        marker = tmp_path / "pwned"
        infodict = {
            "signature": f"x=open({str(marker)!r}, 'w').close()",
            "argnames": ["x"],
            "name": "f",
            "doc": None,
            "module": "m",
            "dict": {},
            "defaults": (),
            "fullsignature": None,
        }
        with pytest.raises(ValueError, match="non-identifier signature"):
            decorators.new_wrapper(lambda *a, **k: None, infodict)
        assert not marker.exists()
        real = decorators._assert_safe_signature
        decorators._assert_safe_signature = lambda signature: None
        try:
            decorators.new_wrapper(lambda *a, **k: None, infodict)
        finally:
            decorators._assert_safe_signature = real
        assert marker.exists(), "without the fence the crafted default ran"


# === 3. read_str: literals only ===
class TestReadStrMatrix:
    @pytest.mark.parametrize(
        "source",
        [
            'f\'{__import__("os").system("true")}\'',
            'f"{1+1}"',
            "b'bytes'",
            "rb'raw'",
            "'a' 'b'",
            "'a'\n'b'",
            "'\\N{LATIN SMALL LETTER A}'",
            "'\\x41\\101\\u0041'",
            "'it''s'",
            "'x' + 'y'",
            "'x'.upper()",
            "(lambda: 1)()",
            "__import__('os')",
            "'" + "x" * 100000 + "'",
        ],
        ids=lambda s: repr(s)[:16],
    )
    def test_no_form_executes_anything(self, source, monkeypatch):
        import builtins

        from nltk.internals import ReadError, read_str

        def _boom(*a, **k):
            raise AssertionError("code executed")

        monkeypatch.setattr(builtins, "eval", _boom)
        monkeypatch.setattr(builtins, "exec", _boom)
        started = time.perf_counter()
        try:
            value, end = read_str(source, 0)
            assert isinstance(value, (str, bytes)) and end <= len(source)
        except (ReadError, ValueError, SyntaxError):
            pass
        assert time.perf_counter() - started < 2.0
