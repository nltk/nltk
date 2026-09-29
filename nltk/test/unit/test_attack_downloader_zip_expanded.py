# Natural Language Toolkit: expanded downloader fetch, verify and unzip attacks
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The downloader's fetch, verify, unzip and status paths and pathsec.ZipFile
extraction, driven against a REAL local HTTP server (http.server on an
ephemeral loopback port, in a thread) and real archives.

Every attack is judged by what reached the disk, the terminal or memory, not
merely by whether something raised: bytes written past a declared size,
files outside the package directory, lines a hostile name forged, live
control characters in captured output, tracemalloc peaks while an index is
parsed. Benign neighbours (a real package installed end to end and loaded
with nltk.data, re-extraction over a single-linked file, a size-0 package)
pin that the guards do not over-block.

The only thing loosened is the SSRF filter, for exactly 127.0.0.1 so the
local server is reachable; every other address still goes through the real
filter. Races are made deterministic by running the attacker's step inside
a wrapper around the call that opens the window; the code under test is
never replaced. Control and bidi characters are built with chr().
"""

import contextlib
import hashlib
import http.server
import io
import ipaddress
import os
import socket
import stat
import threading
import time
import tracemalloc
import unicodedata
import warnings
import zipfile
from xml.sax.saxutils import quoteattr

import pytest

import nltk
import nltk.data
from nltk import downloader, pathsec
from nltk.termsec import sanitize_terminal

ESC = chr(0x1B)
BEL = chr(0x07)
CSI8 = chr(0x9B)
OSC8 = chr(0x9D)
ST8 = chr(0x9C)
NEL = chr(0x85)
LS = chr(0x2028)
PS = chr(0x2029)
RLO = chr(0x202E)
RLE = chr(0x202B)
PDF = chr(0x202C)
ZWSP = chr(0x200B)
CAFE = "caf" + chr(0xE9)
NAIVE = "na" + chr(0xEF) + "ve"
HANZI = chr(0x4E2D) + chr(0x6587)

POSIX_DIR_FD = (
    os.name == "posix"
    and os.open in os.supports_dir_fd
    and bool(getattr(os, "O_NOFOLLOW", 0))
)
needs_dir_fd = pytest.mark.skipif(
    not POSIX_DIR_FD, reason="the hardened extractor needs dir_fd and O_NOFOLLOW"
)
needs_symlink = pytest.mark.skipif(
    not hasattr(os, "symlink") or os.name != "posix", reason="needs POSIX symlinks"
)


# ===========================================================================
# A real HTTP server
# ===========================================================================
class LocalServer:
    """http.server on 127.0.0.1:<ephemeral> serving a route table.

    Every streaming route is capped in bytes and in time, and stops as soon
    as the test ends, so no route can run away with disk, memory or time.
    """

    def __init__(self):
        self.routes = {}
        self.hits = []
        self.sent = {}
        self.stop = threading.Event()
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self):
                server.hits.append(self.path)
                route = server.routes.get(self.path)
                try:
                    if route is None:
                        self.send_error(404)
                    else:
                        route(self)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                self.close_connection = True

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(
            target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}
        )
        self.thread.daemon = True

    def url(self, path):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}{path}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(10)

    # routes
    def body(self, path, data, *, length=None, status=200, reason=None):
        def route(h):
            h.send_response(status, reason)
            h.send_header("Content-Type", "application/octet-stream")
            h.send_header(
                "Content-Length", str(len(data) if length is None else length)
            )
            h.send_header("Connection", "close")
            h.end_headers()
            h.wfile.write(data)

        self.routes[path] = route

    def stream(self, path, unit, cap, *, delay=0.0, chunked=True, length=None):
        """Repeat *unit* up to *cap* bytes (or until the test ends)."""
        frame = (b"%x\r\n" % len(unit) + unit + b"\r\n") if chunked else unit

        def route(h):
            h.send_response(200)
            if chunked:
                h.send_header("Transfer-Encoding", "chunked")
            elif length is not None:
                h.send_header("Content-Length", str(length))
            h.send_header("Connection", "close")
            h.end_headers()
            sent = 0
            deadline = time.monotonic() + 30
            while sent < cap and not self.stop.is_set():
                if time.monotonic() > deadline:
                    break
                h.wfile.write(frame)
                sent += len(unit)
                self.sent[path] = sent
                if delay:
                    time.sleep(delay)
            if chunked:
                h.wfile.write(b"0\r\n\r\n")

        self.routes[path] = route

    def drip(self, path, data, delay):
        """Send *data* one byte at a time, *delay* seconds apart."""

        def route(h):
            h.send_response(200)
            h.send_header("Content-Length", str(len(data)))
            h.send_header("Connection", "close")
            h.end_headers()
            for i in range(len(data)):
                if self.stop.wait(delay):
                    return
                h.wfile.write(data[i : i + 1])

        self.routes[path] = route

    def stall(self, path, length=1000, head=b""):
        """Send the headers (and *head*), then nothing until the test ends."""

        def route(h):
            h.send_response(200)
            h.send_header("Content-Length", str(length))
            h.send_header("Connection", "close")
            h.end_headers()
            h.wfile.write(head)
            self.stop.wait(20)

        self.routes[path] = route

    def truncated(self, path, data, cut):
        """Declare len(data) in Content-Length, send only data[:cut], close."""

        def route(h):
            h.send_response(200)
            h.send_header("Content-Length", str(len(data)))
            h.send_header("Connection", "close")
            h.end_headers()
            h.wfile.write(data[:cut])

        self.routes[path] = route

    def raw(self, path, response):
        """Answer with raw bytes, bypassing http.server's status line."""

        def route(h):
            h.wfile.write(response)

        self.routes[path] = route

    def redirect(self, path, location, status=302):
        def route(h):
            h.send_response(status)
            h.send_header("Location", location)
            h.send_header("Content-Length", "0")
            h.send_header("Connection", "close")
            h.end_headers()

        self.routes[path] = route


@pytest.fixture
def box(pathsec_sandbox, monkeypatch):
    """A private data root, an outside dir under $HOME, a download dir inside
    the root, and a loopback-only allowance for the test server."""
    root, outside = pathsec_sandbox
    dl = root / "dl"
    dl.mkdir()
    real = pathsec._ip_is_forbidden
    loopback = ipaddress.ip_address("127.0.0.1")
    monkeypatch.setattr(
        pathsec, "_ip_is_forbidden", lambda ip: False if ip == loopback else real(ip)
    )
    for var in (
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "all_proxy",
        "ALL_PROXY",
    ):
        monkeypatch.delenv(var, raising=False)
    with LocalServer() as server:
        yield root, outside, dl, server


# ===========================================================================
# Archives, packages and indexes
# ===========================================================================
def make_zip(entries, compression=zipfile.ZIP_DEFLATED):
    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # duplicate names are deliberate here
        with zipfile.ZipFile(buf, "w", compression) as zf:
            for name, data in entries:
                if isinstance(name, zipfile.ZipInfo):
                    info = name
                else:
                    info = zipfile.ZipInfo(name)
                    info.compress_type = compression
                zf.writestr(info, data)
    return buf.getvalue()


def patch_declared_size(blob, name, file_size):
    """Rewrite *name*'s declared uncompressed size in both zip headers."""
    data = bytearray(blob)
    encoded = name.encode()
    pos = data.find(b"PK\x03\x04")
    while pos != -1:
        nlen = int.from_bytes(data[pos + 26 : pos + 28], "little")
        if bytes(data[pos + 30 : pos + 30 + nlen]) == encoded:
            data[pos + 22 : pos + 26] = file_size.to_bytes(4, "little")
        pos = data.find(b"PK\x03\x04", pos + 4)
    pos = data.find(b"PK\x01\x02")
    while pos != -1:
        nlen = int.from_bytes(data[pos + 28 : pos + 30], "little")
        if bytes(data[pos + 46 : pos + 46 + nlen]) == encoded:
            data[pos + 24 : pos + 28] = file_size.to_bytes(4, "little")
        pos = data.find(b"PK\x01\x02", pos + 4)
    return bytes(data)


def package_attrs(pid, blob, url, *, subdir="corpora", unzip="1", **extra):
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            unzipped = sum(info.file_size for info in zf.infolist())
    except zipfile.BadZipFile:
        unzipped = len(blob)
    attrs = {
        "id": pid,
        "name": pid,
        "subdir": subdir,
        "url": url,
        "size": str(len(blob)),
        "unzipped_size": str(unzipped),
        "checksum": hashlib.md5(blob).hexdigest(),
        "sha256_checksum": hashlib.sha256(blob).hexdigest(),
        "unzip": unzip,
    }
    attrs.update(extra)
    return attrs


def xml_attr(value):
    return quoteattr(str(value), {"\n": "&#10;", "\r": "&#13;", "\t": "&#9;"})


def make_index(packages=(), collections=()):
    out = ['<?xml version="1.0" encoding="utf-8"?>\n<nltk_data>\n<packages>\n']
    for attrs in packages:
        out.append(
            "<package "
            + " ".join(f"{k}={xml_attr(v)}" for k, v in attrs.items())
            + " />\n"
        )
    out.append("</packages>\n<collections>\n")
    for cid, refs in collections:
        items = "".join(f"<item ref={xml_attr(ref)} />" for ref in refs)
        out.append(
            f"<collection id={xml_attr(cid)} name={xml_attr(cid)}>{items}</collection>\n"
        )
    out.append("</collections>\n</nltk_data>\n")
    return "".join(out).encode("utf-8")


def serve_packages(server, packages, collections=()):
    """Serve (pid, blob, extra-attrs) packages and their index; return the
    index URL."""
    attrs = []
    for pid, blob, extra in packages:
        path = f"/pkgs/{pid}.zip"
        server.body(path, blob)
        attrs.append(package_attrs(pid, blob, server.url(path), **extra))
    server.body("/index.xml", make_index(attrs, collections))
    return server.url("/index.xml")


def run_download(index_url, dl, target, **kw):
    """nltk's own Downloader.download against the server; returns (result,
    everything it wrote to stdout and to the error stream)."""
    d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out):
        result = d.download(target, download_dir=str(dl), print_error_to=err, **kw)
    return result, out.getvalue() + err.getvalue()


def tree(path):
    """Every entry under *path*, relative, with lstat type and size."""
    found = {}
    if not os.path.lexists(path):
        return found
    for top, dirs, files in os.walk(path):
        for name in dirs + files:
            full = os.path.join(top, name)
            st = os.lstat(full)
            found[os.path.relpath(full, path)] = (stat.S_IFMT(st.st_mode), st.st_size)
    return found


def assert_lines_clean(text, expected_lines=None):
    """Nothing a terminal would act on survives in any displayed line."""
    lines = text.split("\n")
    for line in lines:
        assert sanitize_terminal(line, single_line=True) == line, repr(line)
    if expected_lines is not None:
        assert len([line for line in lines if line]) == expected_lines, lines


def traced_peak(fn):
    """Run *fn* under tracemalloc; return (outcome, peak bytes)."""
    tracemalloc.start()
    try:
        try:
            outcome = fn()
        except Exception as exc:  # the outcome IS the refusal
            outcome = exc
        return outcome, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


WORDS = b"alpha\nbeta\ngamma\n"


def tiny_package(pid="tiny"):
    return make_zip([(f"{pid}/", b""), (f"{pid}/words.txt", WORDS)])


# ===========================================================================
# 1. The package body: declared size, endless and short bodies, bad sizes
# ===========================================================================
class TestPackageBody:
    def _drive(self, index_url, dl, pid):
        """Run _download_package, sampling the temp file at every yield."""
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        info = d.info(pid)
        tmp = os.path.join(str(dl), info.filename) + ".tmp"
        peak, messages = 0, []
        for message in d._download_package(info, str(dl), force=True):
            messages.append(message)
            with contextlib.suppress(FileNotFoundError):
                peak = max(peak, os.lstat(tmp).st_size)
        return info, messages, peak

    def _nothing_committed(self, dl, info):
        final = os.path.join(str(dl), info.filename)
        assert not os.path.exists(final)
        assert not os.path.exists(final + ".tmp")
        assert not os.path.exists(final + ".lock")
        assert not os.path.exists(final[:-4])

    def test_endless_chunked_body_never_passes_the_declared_size_on_disk(self, box):
        root, outside, dl, server = box
        blob = tiny_package()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"))
        server.body("/index.xml", make_index([attrs]))
        server.stream("/pkgs/tiny.zip", b"Z" * 65536, cap=8 * 1024 * 1024)
        info, messages, peak = self._drive(server.url("/index.xml"), dl, "tiny")
        assert any(isinstance(m, downloader.ErrorMessage) for m in messages)
        assert peak <= len(blob), f"{peak} bytes reached disk for a {len(blob)}"
        self._nothing_committed(dl, info)

    @pytest.mark.parametrize(
        "shape",
        ["longer_with_length", "one_extra_byte", "chunk_aligned_extra", "shorter"],
    )
    def test_a_body_that_is_not_exactly_the_declared_size_is_refused(self, box, shape):
        root, outside, dl, server = box
        blob = tiny_package()
        if shape == "chunk_aligned_extra":
            # a declared size that is a whole number of read blocks, then more
            blob = make_zip([("tiny/pad.bin", os.urandom(16384 - 118))])
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"))
        server.body("/index.xml", make_index([attrs]))
        body = {
            "longer_with_length": blob + b"X" * 5000,
            "one_extra_byte": blob + b"X",
            "chunk_aligned_extra": blob + b"Y" * 16384,
            "shorter": blob[:-10],
        }[shape]
        server.body("/pkgs/tiny.zip", body)
        info, messages, peak = self._drive(server.url("/index.xml"), dl, "tiny")
        assert any(isinstance(m, downloader.ErrorMessage) for m in messages)
        assert peak <= len(blob)
        self._nothing_committed(dl, info)

    def test_a_body_cut_short_of_its_content_length_is_a_reported_failure(self, box):
        root, outside, dl, server = box
        blob = tiny_package()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"))
        server.body("/index.xml", make_index([attrs]))
        server.truncated("/pkgs/tiny.zip", blob, len(blob) // 2)
        result, output = run_download(server.url("/index.xml"), dl, "tiny")
        assert result is False
        assert "Error downloading" in output or "Integrity check failed" in output
        assert not os.path.exists(os.path.join(str(dl), "corpora", "tiny.zip"))
        assert not os.path.exists(os.path.join(str(dl), "corpora", "tiny.zip.lock"))

    @pytest.mark.parametrize(
        "size",
        ["-1", str(downloader.MAX_PACKAGE_BYTES + 1), str(2**63), "9" * 30],
    )
    def test_an_out_of_range_declared_size_requests_nothing(self, box, size):
        root, outside, dl, server = box
        blob = tiny_package()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"), size=size)
        server.body("/index.xml", make_index([attrs]))
        server.stream("/pkgs/tiny.zip", b"Z" * 65536, cap=4 * 1024 * 1024)
        result, output = run_download(server.url("/index.xml"), dl, "tiny")
        assert result is False and "Refusing to download" in output
        assert "/pkgs/tiny.zip" not in server.hits
        assert tree(str(dl / "corpora")) == {}

    @pytest.mark.parametrize("size", ["1.5", "1e3", "", "0x10", "NaN", "ten", "inf"])
    def test_a_non_integer_declared_size_refuses_the_index(self, box, size):
        root, outside, dl, server = box
        blob = tiny_package()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"), size=size)
        server.body("/index.xml", make_index([attrs]))
        server.body("/pkgs/tiny.zip", blob)
        result, output = run_download(server.url("/index.xml"), dl, "tiny")
        assert result is False
        assert "/pkgs/tiny.zip" not in server.hits
        assert not (dl / "corpora").exists()

    @pytest.mark.parametrize("size", [float("nan"), float("inf"), "x", None])
    def test_a_programmatic_package_with_a_bad_size_is_reported_not_raised(
        self, box, size
    ):
        root, outside, dl, server = box
        package = downloader.Package(
            id="tiny",
            url=server.url("/pkgs/tiny.zip"),
            subdir="corpora",
            size=1,
            unzipped_size=1,
        )
        package.size = size
        messages = list(
            downloader.Downloader(download_dir=str(dl))._download_package(
                package, str(dl), force=True
            )
        )
        assert any(isinstance(m, downloader.ErrorMessage) for m in messages)
        assert "/pkgs/tiny.zip" not in server.hits

    def test_a_zero_byte_package_installs_and_a_zero_declared_size_bounds_it(self, box):
        root, outside, dl, server = box
        empty = package_attrs(
            "empty",
            b"",
            server.url("/pkgs/empty.txt"),
            unzip="0",
            unzipped_size="0",
        )
        liar = package_attrs(
            "liar", b"", server.url("/pkgs/liar.txt"), unzip="0", unzipped_size="0"
        )
        server.body("/index.xml", make_index([empty, liar]))
        server.body("/pkgs/empty.txt", b"")
        server.stream("/pkgs/liar.txt", b"L" * 4096, cap=1024 * 1024, chunked=True)
        result, output = run_download(server.url("/index.xml"), dl, "empty")
        assert result is True, output
        assert os.path.getsize(os.path.join(str(dl), "corpora", "empty.txt")) == 0
        result, output = run_download(server.url("/index.xml"), dl, "liar")
        assert result is False
        assert not os.path.exists(os.path.join(str(dl), "corpora", "liar.txt"))

    def test_a_stalled_package_body_times_out(self, box, monkeypatch):
        root, outside, dl, server = box
        monkeypatch.setattr(downloader, "NETWORK_TIMEOUT", 1)
        blob = tiny_package()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"))
        server.body("/index.xml", make_index([attrs]))
        server.stall("/pkgs/tiny.zip", length=len(blob), head=blob[:10])
        started = time.monotonic()
        result, output = run_download(server.url("/index.xml"), dl, "tiny")
        assert time.monotonic() - started < 8
        assert result is False
        assert not os.path.exists(os.path.join(str(dl), "corpora", "tiny.zip"))
        assert not os.path.exists(os.path.join(str(dl), "corpora", "tiny.zip.tmp"))


# ===========================================================================
# 2. The index: size, time, structure, entities, redirects, raw responses
# ===========================================================================
class TestIndex:
    def _load(self, url, dl):
        d = downloader.Downloader(server_index_url=url, download_dir=str(dl))
        d._update_index()
        return d

    def test_an_endless_chunked_index_is_refused_at_the_real_ceiling(self, box):
        root, outside, dl, server = box
        cap = downloader.MAX_INDEX_BYTES + 8 * 1024 * 1024
        server.stream("/index.xml", b"<x>" * 21845, cap=cap)
        outcome, peak = traced_peak(lambda: self._load(server.url("/index.xml"), dl))
        assert isinstance(outcome, ValueError) and "larger than" in str(outcome)
        assert peak <= downloader.MAX_INDEX_BYTES + 16 * 1024 * 1024, peak

    def test_an_oversized_index_with_a_content_length_is_refused(self, box):
        root, outside, dl, server = box
        size = downloader.MAX_INDEX_BYTES + 65536
        server.stream("/index.xml", b" " * 65536, cap=size, chunked=False, length=size)
        with pytest.raises(ValueError, match="larger than"):
            self._load(server.url("/index.xml"), dl)

    def test_a_drip_fed_index_is_refused_by_its_deadline(self, box, monkeypatch):
        root, outside, dl, server = box
        monkeypatch.setattr(downloader, "INDEX_DEADLINE", 1.0)
        body = make_index([]) + b" " * 300  # about 20 s at this drip
        server.drip("/index.xml", body, delay=0.05)
        started = time.monotonic()
        with pytest.raises(ValueError, match="time budget"):
            self._load(server.url("/index.xml"), dl)
        assert time.monotonic() - started < 6

    def test_a_stalled_index_times_out(self, box, monkeypatch):
        root, outside, dl, server = box
        monkeypatch.setattr(downloader, "NETWORK_TIMEOUT", 1)
        server.stall("/index.xml", length=5000, head=b"<?xml")
        started = time.monotonic()
        with pytest.raises((OSError, ValueError)):
            self._load(server.url("/index.xml"), dl)
        assert time.monotonic() - started < 8

    def test_an_entity_bomb_is_refused_without_expanding(self, box):
        root, outside, dl, server = box
        lol = ['<!ENTITY l0 "lol">'] + [
            f'<!ENTITY l{i} "{("&l%d;" % (i - 1)) * 10}">' for i in range(1, 10)
        ]
        body = (
            '<?xml version="1.0"?><!DOCTYPE nltk_data [' + "".join(lol) + "]>"
            "<nltk_data><packages/><collections>&l9;</collections></nltk_data>"
        ).encode()
        server.body("/index.xml", body)
        outcome, peak = traced_peak(lambda: self._load(server.url("/index.xml"), dl))
        assert isinstance(outcome, ValueError), outcome
        assert peak < 8 * 1024 * 1024, peak

    def test_an_external_entity_does_not_read_a_local_file(self, box):
        root, outside, dl, server = box
        secret = outside / "secret.txt"
        secret.write_text("TOPSECRET")
        body = (
            '<?xml version="1.0"?><!DOCTYPE nltk_data [<!ENTITY x SYSTEM '
            f'"{secret.as_uri()}">]><nltk_data><packages><package id="p" '
            'name="&x;" url="http://127.0.0.1/p.zip" size="1" unzipped_size="1" '
            'subdir="corpora"/></packages><collections/></nltk_data>'
        ).encode()
        server.body("/index.xml", body)
        with pytest.raises(ValueError):
            self._load(server.url("/index.xml"), dl)

    def test_an_element_flood_inside_the_byte_ceiling_is_refused_small(self, box):
        root, outside, dl, server = box
        body = (
            b"<nltk_data><packages>"
            + b"<p/>" * (1024 * 1024)
            + b"</packages><collections/></nltk_data>"
        )
        server.body("/index.xml", body)
        outcome, peak = traced_peak(lambda: self._load(server.url("/index.xml"), dl))
        assert isinstance(outcome, ValueError), outcome
        assert peak < 4 * len(body), f"peak {peak} for a {len(body)} byte index"

    def test_an_attribute_flood_in_one_tag_is_refused_small(self, box):
        root, outside, dl, server = box
        attrs = b" ".join(b'a%07d=""' % i for i in range(250_000))
        body = b"<nltk_data " + attrs + b"><packages/><collections/></nltk_data>"
        server.body("/index.xml", body)
        outcome, peak = traced_peak(lambda: self._load(server.url("/index.xml"), dl))
        assert isinstance(outcome, ValueError), outcome
        assert peak < 4 * len(body), f"peak {peak} for a {len(body)} byte index"

    def test_dtd_default_attributes_cannot_multiply_the_tree(self, box):
        # No entity is declared, so an entity filter lets this through: every
        # <p/> silently gains 200 attributes from the ATTLIST defaults.
        root, outside, dl, server = box
        defaults = " ".join(f'a{i} CDATA "v"' for i in range(200))
        body = (
            f'<?xml version="1.0"?><!DOCTYPE nltk_data [<!ATTLIST p {defaults}>]>'
            "<nltk_data><packages>" + "<p/>" * 2000 + "</packages>"
            "<collections/></nltk_data>"
        ).encode()
        server.body("/index.xml", body)
        outcome, peak = traced_peak(lambda: self._load(server.url("/index.xml"), dl))
        assert isinstance(outcome, ValueError), outcome
        assert peak < 2 * 1024 * 1024, f"peak {peak} for a {len(body)} byte index"

    def test_an_index_shaped_like_the_real_one_at_ten_times_its_size_loads(self, box):
        root, outside, dl, server = box
        packages = [
            package_attrs(
                f"pkg{i:04d}",
                b"x" * 10,
                f"https://example.invalid/p{i}.zip",
                webpage="https://example.invalid/",
                license="Unknown",
                author="Someone",
                note="a" * 200,
            )
            for i in range(1220)
        ]
        collections = [
            (f"col{i}", [f"pkg{j:04d}" for j in range(i, 1220, 7)]) for i in range(7)
        ]
        server.body("/index.xml", make_index(packages, collections))
        d = self._load(server.url("/index.xml"), dl)
        assert len(d._packages) == 1220 and len(d._collections) == 7

    @pytest.mark.parametrize(
        "location",
        [
            "OUTSIDE_FILE",
            "ROOT_FILE",
            "ftp://127.0.0.1/x.zip",
            "data:application/zip;base64,UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==",
            "gopher://127.0.0.1:70/x",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/x.zip",
            "http://[::1]/x.zip",
            "http://0x7f.1/x.zip",
            "LOOP",
            "CHAIN",
        ],
    )
    def test_a_package_redirect_off_the_http_world_is_refused(self, box, location):
        root, outside, dl, server = box
        secret = outside / "secret.zip"
        secret.write_bytes(tiny_package())
        mirror = root / "mirror.zip"
        mirror.write_bytes(tiny_package())
        blob = secret.read_bytes()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"))
        server.body("/index.xml", make_index([attrs]))
        if location == "LOOP":
            server.redirect("/pkgs/tiny.zip", server.url("/pkgs/tiny.zip"))
        elif location == "CHAIN":
            for hop in range(15):
                server.redirect(f"/hop{hop}", server.url(f"/hop{hop + 1}"))
            server.redirect("/pkgs/tiny.zip", server.url("/hop0"))
            server.body("/hop15", blob)
        else:
            target = {
                "OUTSIDE_FILE": secret.as_uri(),
                "ROOT_FILE": mirror.as_uri(),
            }.get(location, location)
            server.redirect("/pkgs/tiny.zip", target)
        result, output = run_download(server.url("/index.xml"), dl, "tiny")
        assert result is False
        assert tree(str(dl / "corpora")) == {}
        assert secret.read_bytes() == blob

    def test_an_index_redirect_to_a_file_url_is_refused(self, box):
        root, outside, dl, server = box
        planted = outside / "index.xml"
        planted.write_bytes(make_index([]))
        server.redirect("/index.xml", planted.as_uri())
        with pytest.raises((OSError, ValueError)):
            self._load(server.url("/index.xml"), dl)

    def test_a_raw_malformed_index_response_is_reported_sanitised(self, box):
        root, outside, dl, server = box
        server.raw("/index.xml", (ESC + "]0;pwned" + BEL + " junk\r\n\r\n").encode())
        err = io.StringIO()
        out = io.StringIO()
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        with contextlib.redirect_stdout(out):
            result = d.download("tiny", download_dir=str(dl), print_error_to=err)
        assert result is False
        assert_lines_clean(out.getvalue() + err.getvalue())
        with pytest.raises(ValueError) as caught:
            d.download(
                "tiny", download_dir=str(dl), print_error_to=err, raise_on_error=True
            )
        assert_lines_clean(str(caught.value))

    def test_an_index_redirect_to_an_internal_address_is_refused(self, box):
        root, outside, dl, server = box
        server.redirect("/index.xml", "http://169.254.169.254/latest/meta-data/")
        with pytest.raises((OSError, ValueError)):
            self._load(server.url("/index.xml"), dl)

    @pytest.mark.parametrize(
        "field, value",
        [
            ("url", "http://127.0.0.1/p.zip" + chr(10)),
            ("url", "http://127.0.0.1/p.z" + NEL + "ip"),
            ("subdir", "corpora" + chr(10) + "x"),
            ("subdir", "corp" + RLO + "ora"),
            ("id", "tiny" + ZWSP),
        ],
    )
    def test_an_index_file_name_a_terminal_would_act_on_is_refused(
        self, box, field, value
    ):
        root, outside, dl, server = box
        attrs = package_attrs("tiny", b"x", server.url("/pkgs/tiny.zip"))
        attrs[field] = value
        server.body("/index.xml", make_index([attrs]))
        with pytest.raises(ValueError, match="CWE-150"):
            self._load(server.url("/index.xml"), dl)
        assert not (dl / "corpora").exists()

    def test_a_utf16_index_loads_and_its_floods_are_still_counted(self, box):
        root, outside, dl, server = box
        attrs = package_attrs("tiny", b"x", server.url("/pkgs/tiny.zip"))
        text = (
            make_index([attrs])
            .decode()
            .replace('encoding="utf-8"', 'encoding="utf-16"')
        )
        server.body("/index.xml", text.encode("utf-16"))
        assert "tiny" in self._load(server.url("/index.xml"), dl)._packages
        flood = (
            '<?xml version="1.0" encoding="utf-16"?><nltk_data><packages>'
            + "<p/>" * (256 * 1024)
            + "</packages><collections/></nltk_data>"
        ).encode("utf-16")
        server.body("/flood.xml", flood)
        outcome, peak = traced_peak(lambda: self._load(server.url("/flood.xml"), dl))
        assert isinstance(outcome, ValueError), outcome
        assert peak < 4 * len(flood), peak

    def test_self_and_mutually_referential_collections_download_bounded(self, box):
        root, outside, dl, server = box
        index_url = serve_packages(
            server,
            [("tiny", tiny_package(), {})],
            collections=[
                ("self", ["self", "tiny"]),
                ("a", ["b"]),
                ("b", ["a"]),
                ("empty", []),
            ],
        )
        for target in ("self", "a", "empty"):
            result, output = run_download(index_url, dl, target)
            assert result is True, (target, output)
            assert output.count("Downloading collection") <= 2, output
        assert (dl / "corpora" / "tiny" / "words.txt").read_bytes() == WORDS


# ===========================================================================
# 3. The terminal: hostile ids, names, refs and reasons through the real paths
# ===========================================================================
LINE_BREAKS = {"lf": "\n", "cr": "\r", "nel": NEL, "ls": LS, "ps": PS, "tab": "\t"}
DISPLAY_ATTACKS = {
    **LINE_BREAKS,
    "csi8_clear": CSI8 + "2J",
    "osc8_clipboard": OSC8 + "52;c;aGVsbG8=" + ST8,
    "rlo": RLO + "txt.exe",
    "rle_unbalanced": RLE + "abc",
    "zwsp": ZWSP,
}


class TestTerminal:
    def test_hostile_package_names_never_reach_list_unsanitised(self, box):
        root, outside, dl, server = box
        packages = []
        for n, payload in enumerate(DISPLAY_ATTACKS.values()):
            packages.append(
                package_attrs(
                    f"n{n:02d}",
                    b"x",
                    server.url(f"/p{n}.zip"),
                    name=f"Name{n} [*] fake{payload}[*] installed{payload}end",
                )
            )
        # bidi that is balanced overall but opens on one wrapped line and
        # closes on the next
        packages.append(
            package_attrs(
                "wrap",
                b"x",
                server.url("/w.zip"),
                name="A " * 30 + RLE + " right" * 20 + PDF,
            )
        )
        server.body("/index.xml", make_index(packages))
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            d.list(download_dir=str(dl), show_collections=False)
        text = out.getvalue()
        assert_lines_clean(text)
        rows = [line for line in text.split("\n") if line.startswith("  [")]
        assert len(rows) == len(packages), rows

    @pytest.mark.parametrize("label", sorted(DISPLAY_ATTACKS))
    def test_a_hostile_package_id_in_the_index_forges_no_line(self, box, label):
        root, outside, dl, server = box
        good = package_attrs("good", b"x", server.url("/g.zip"))
        evil = package_attrs(
            "evil" + DISPLAY_ATTACKS[label] + "  [*] punkt",
            b"x",
            server.url("/e.zip"),
        )
        server.body("/index.xml", make_index([good, evil]))
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                d.list(download_dir=str(dl), show_collections=False)
            except ValueError:
                pass  # refusing the whole index is a sound outcome
        text = out.getvalue()
        assert_lines_clean(text)
        rows = [line for line in text.split("\n") if line.startswith("  [")]
        # one row per package at most, and no row forged to open with a mark
        assert len(rows) <= 2, rows
        assert not any(line.lstrip().startswith("[*]") for line in text.split("\n"))

    @pytest.mark.parametrize("label", sorted(DISPLAY_ATTACKS))
    def test_a_hostile_collection_id_forges_no_line(self, box, label):
        root, outside, dl, server = box
        good = package_attrs("good", b"x", server.url("/g.zip"))
        server.body(
            "/index.xml",
            make_index(
                [good],
                [("col" + DISPLAY_ATTACKS[label] + "  [*] all", ["good"])],
            ),
        )
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                d.list(download_dir=str(dl))
            except ValueError:
                pass
        text = out.getvalue()
        assert_lines_clean(text)
        assert not any(line.lstrip().startswith("[*]") for line in text.split("\n"))
        rows = [line for line in text.split("\n") if line.startswith("  [")]
        assert len(rows) <= 2, rows

    def test_dangling_collection_refs_print_one_clean_line_each_and_all_go(self, box):
        root, outside, dl, server = box
        good = package_attrs("good", b"x", server.url("/g.zip"))
        refs = ["good"] + [
            "missing" + payload + "[nltk_data] Done"
            for payload in DISPLAY_ATTACKS.values()
        ]
        server.body("/index.xml", make_index([good], [("col", refs)]))
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            d._update_index()
        text = out.getvalue()
        assert_lines_clean(text, expected_lines=len(DISPLAY_ATTACKS))
        children = d._collections["col"].children
        assert [c.id for c in children] == ["good"], children

    def test_show_output_and_raised_text_stay_clean_for_a_hostile_reason(self, box):
        root, outside, dl, server = box
        blob = tiny_package()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"))
        server.body("/index.xml", make_index([attrs]))
        reason = "Gone" + ESC + "]52;c;aGVsbG8=" + BEL + ESC + "[2J" + CSI8 + "H"
        server.body("/pkgs/tiny.zip", b"", status=404, reason=reason)
        result, output = run_download(server.url("/index.xml"), dl, "tiny")
        assert result is False
        assert_lines_clean(output)
        with pytest.raises(ValueError) as caught:
            run_download(server.url("/index.xml"), dl, "tiny", raise_on_error=True)
        assert_lines_clean(str(caught.value))

    def test_a_raw_status_line_with_escapes_is_a_reported_failure(self, box):
        root, outside, dl, server = box
        blob = tiny_package()
        attrs = package_attrs("tiny", blob, server.url("/pkgs/tiny.zip"))
        server.body("/index.xml", make_index([attrs]))
        server.raw("/pkgs/tiny.zip", (ESC + "]0;pwned" + BEL + " x\r\n\r\n").encode())
        result, output = run_download(server.url("/index.xml"), dl, "tiny")
        assert result is False
        assert_lines_clean(output)
        assert tree(str(dl / "corpora")) == {}

    def test_a_hostile_member_name_in_a_refusal_stays_clean(self, box):
        root, outside, dl, server = box
        evil = "../" + ESC + "]52;c;aGk=" + BEL + "x" + RLO + ".txt"
        blob = make_zip([("tiny/ok.txt", b"ok"), (evil, b"x")])
        index_url = serve_packages(server, [("tiny", blob, {})])
        result, output = run_download(index_url, dl, "tiny")
        assert result is False
        assert_lines_clean(output)
        with pytest.raises(ValueError) as caught:
            run_download(index_url, dl, "tiny", raise_on_error=True)
        assert_lines_clean(str(caught.value))

    @pytest.mark.parametrize("label", sorted(DISPLAY_ATTACKS) + ["esc", "osc52"])
    def test_show_for_a_programmatic_package_is_clean(self, box, label):
        root, outside, dl, server = box
        payload = {"esc": ESC + "[2J", "osc52": ESC + "]52;c;aGk=" + BEL}.get(
            label, DISPLAY_ATTACKS.get(label)
        )
        package = downloader.Package(
            id="prog",
            url=server.url("/nope.zip"),
            subdir="corpora",
            size=1,
            unzipped_size=1,
        )
        package.id = "prog" + payload + "[nltk_data] Done"
        err = io.StringIO()
        result = downloader.Downloader(download_dir=str(dl)).download(
            package, download_dir=str(dl), print_error_to=err
        )
        assert result is False
        assert_lines_clean(err.getvalue())
        corpora = dl / "corpora"
        assert not corpora.exists() or tree(str(corpora)) == {}

    def test_show_balances_bidi_per_wrapped_line(self, box):
        root, outside, dl, server = box
        package = downloader.Package(
            id="prog",
            url=server.url("/nope.zip"),
            subdir="corpora",
            size=1,
            unzipped_size=1,
        )
        package.id = "prog " + "w " * 40 + RLE + " z" * 30 + PDF
        err = io.StringIO()
        downloader.Downloader(download_dir=str(dl)).download(
            package, download_dir=str(dl), print_error_to=err
        )
        assert_lines_clean(err.getvalue())


# A numeric character reference is exempt from XML attribute-value
# normalisation, so the entity form of a line break reaches Python as the real
# character, unlike a literal one, which the parser turns into a space.
ENTITY_BREAKS = {
    "lf-dec": ("&#10;", "\n"),
    "lf-hex": ("&#xA;", "\n"),
    "lf-hex-lower": ("&#x0a;", "\n"),
    "cr": ("&#13;", "\r"),
    "crlf": ("&#13;&#10;", "\r\n"),
    "tab": ("&#9;", "\t"),
    "nel-hex": ("&#x85;", NEL),
    "nel-dec": ("&#133;", NEL),
    "ls": ("&#x2028;", LS),
    "ps": ("&#x2029;", PS),
}
FORGED = "FORGED-SECOND-PART"


def entity_index(package_id="good", name="Good", collection_id="col", refs=("good",)):
    """An index written by hand, so each entity reaches the parser verbatim."""
    items = "".join(f'<item ref="{ref}"/>' for ref in refs)
    return (
        '<?xml version="1.0" encoding="utf-8"?><nltk_data><packages>'
        f'<package id="{package_id}" name="{name}" subdir="corpora" '
        'url="http://127.0.0.1/p.zip" size="1" unzipped_size="1" '
        'checksum="0" sha256_checksum="0"/></packages><collections>'
        f'<collection id="{collection_id}" name="C">{items}</collection>'
        "</collections></nltk_data>"
    ).encode()


def assert_no_forged_line(text):
    for line in text.split("\n"):
        assert not line.lstrip().startswith(FORGED), repr(text)
    assert_lines_clean(text)


class TestEntityFormLineBreaks:
    @pytest.mark.parametrize("label", sorted(ENTITY_BREAKS))
    def test_a_dangling_ref_prints_one_prefixed_line(self, box, label):
        # the review's reproduction, for every line-break entity
        root, outside, dl, server = box
        entity, raw = ENTITY_BREAKS[label]
        refs = ("good", f"evilrefFIRST-LINE{entity}{FORGED}", f"two{entity}{FORGED}")
        server.body("/index.xml", entity_index(refs=refs))
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            d._update_index()
        lines = [line for line in out.getvalue().split("\n") if line]
        assert len(lines) == 2, lines
        assert all(
            line.startswith("removing collection member with no package: ")
            for line in lines
        ), lines
        assert_no_forged_line(out.getvalue())
        assert [c.id for c in d._collections["col"].children] == ["good"]

    @pytest.mark.parametrize("label", sorted(ENTITY_BREAKS))
    def test_a_package_name_forges_no_list_line(self, box, label):
        root, outside, dl, server = box
        entity, raw = ENTITY_BREAKS[label]
        name = f"Good FIRST{entity}{FORGED} " + "wrap " * 12 + f"x{entity}{FORGED}"
        server.body("/index.xml", entity_index(name=name))
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        d._update_index()
        assert raw in d._packages["good"].name  # the entity really survived
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            d.list(download_dir=str(dl))
        assert_no_forged_line(out.getvalue())
        rows = [line for line in out.getvalue().split("\n") if line.startswith("  [")]
        assert len(rows) == 2, rows  # the package and the collection

    @pytest.mark.parametrize("label", sorted(ENTITY_BREAKS))
    @pytest.mark.parametrize("field", ["package_id", "collection_id"])
    def test_an_id_holding_one_is_refused_and_forges_nothing(self, box, label, field):
        root, outside, dl, server = box
        entity, raw = ENTITY_BREAKS[label]
        kw = {field: f"x{entity}{FORGED}"}
        if field == "package_id":
            kw["refs"] = (kw["package_id"],)
        server.body("/index.xml", entity_index(**kw))
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out):
            with pytest.raises(ValueError, match="CWE-150"):
                d.list(download_dir=str(dl))
            assert d.download("good", download_dir=str(dl), print_error_to=err) is False
        assert_no_forged_line(out.getvalue() + err.getvalue())

    @pytest.mark.parametrize("label", sorted(ENTITY_BREAKS))
    def test_show_keeps_every_line_behind_its_prefix(self, box, label):
        root, outside, dl, server = box
        entity, raw = ENTITY_BREAKS[label]
        server.body("/index.xml", entity_index())
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        err = io.StringIO()
        # a caller-supplied id quoted back in the error, and a package object
        # whose id holds the parsed character, both through show()
        d.download(f"missing{raw}{FORGED}", download_dir=str(dl), print_error_to=err)
        package = downloader.Package(
            id="prog",
            url=server.url("/nope.zip"),
            subdir="corpora",
            size=1,
            unzipped_size=1,
        )
        package.id = f"prog{raw}{FORGED}"
        d.download(package, download_dir=str(dl), print_error_to=err)
        text = err.getvalue()
        assert_no_forged_line(text)
        assert all(line.startswith("[nltk_data] ") for line in text.split("\n") if line)


# ===========================================================================
# 4. Extraction through the real downloader
# ===========================================================================
def install(server, dl, pid, entries, **kw):
    blob = make_zip(entries)
    index_url = serve_packages(server, [(pid, blob, kw.pop("extra", {}))])
    return run_download(index_url, dl, pid, **kw)


class TestUnzip:
    def test_a_hardlink_planted_at_a_member_target_is_refused(self, box):
        root, outside, dl, server = box
        secret = outside / "secret.txt"
        secret.write_bytes(b"ORIGINAL")
        pkgdir = dl / "corpora" / "tiny"
        pkgdir.mkdir(parents=True)
        try:
            os.link(secret, pkgdir / "words.txt")
        except OSError:
            pytest.skip("cannot hardlink across these directories")
        result, output = install(server, dl, "tiny", [("tiny/words.txt", b"EVILEVIL")])
        assert result is False
        assert secret.read_bytes() == b"ORIGINAL"

    @needs_symlink
    def test_a_symlink_member_is_written_as_a_plain_file(self, box):
        root, outside, dl, server = box
        link = zipfile.ZipInfo("tiny/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        target = os.path.relpath(str(outside), str(dl / "corpora" / "tiny"))
        result, output = install(
            server,
            dl,
            "tiny",
            [("tiny/", b""), (link, target.encode()), ("tiny/words.txt", WORDS)],
        )
        assert result is True, output
        placed = dl / "corpora" / "tiny" / "link"
        assert not placed.is_symlink() and placed.read_bytes() == target.encode()
        assert list(outside.iterdir()) == []

    @pytest.mark.parametrize(
        "name",
        [
            "../x.txt",
            "tiny/../../x.txt",
            "/tiny/x.txt",
            "tiny/../other/x.txt",
            "tiny/sub/../../../x.txt",
            "tiny\\..\\..\\x.txt",
            "tiny\\sub\\..\\..\\..\\x.txt",
            "C:/x.txt",
            "C:\\x.txt",
            "\\\\server\\share\\x.txt",
            "other/x.txt",
            "",
        ],
    )
    def test_a_traversing_member_is_refused_before_anything_is_written(self, box, name):
        root, outside, dl, server = box
        result, output = install(
            server, dl, "tiny", [("tiny/aaa.txt", b"first"), (name or "/", b"x")]
        )
        assert result is False, output
        assert not (dl / "corpora" / "tiny").exists(), tree(str(dl / "corpora"))
        assert list(outside.iterdir()) == []
        assert not os.path.exists(os.path.join(str(dl), "x.txt"))

    @needs_symlink
    def test_a_backslash_member_cannot_ride_a_planted_symlink(self, box):
        root, outside, dl, server = box
        pkgdir = dl / "corpora" / "tiny"
        pkgdir.mkdir(parents=True)
        os.symlink(str(outside), str(pkgdir / "sub"))
        result, output = install(
            server, dl, "tiny", [("tiny\\sub\\x.txt", b"x"), ("tiny/words.txt", WORDS)]
        )
        assert result is False
        assert list(outside.iterdir()) == []

    @pytest.mark.parametrize(
        "entries",
        [
            [("tiny/a.txt", b"benign"), ("tiny/a.txt", b"EVIL")],
            [("tiny/Weights.json", b"benign"), ("tiny/weights.json", b"EVIL")],
            [
                ("tiny/" + unicodedata.normalize("NFC", CAFE + ".txt"), b"benign"),
                ("tiny/" + unicodedata.normalize("NFD", CAFE + ".txt"), b"EVIL"),
            ],
            [("tiny/x/", b""), ("tiny/x", b"EVIL")],
            [("tiny/x", b"benign"), ("tiny/x/y", b"EVIL")],
            [("tiny/X", b"benign"), ("tiny/x/y", b"EVIL")],
            [("tiny/a.txt", b"benign"), ("tiny//a.txt", b"EVIL")],
            [("tiny/a.txt", b"benign"), ("tiny/./a.txt", b"EVIL")],
        ],
        ids=[
            "duplicate",
            "case",
            "nfc-nfd",
            "dir-then-file",
            "file-then-child",
            "case-file-then-child",
            "double-slash",
            "dot-segment",
        ],
    )
    def test_members_landing_on_one_file_are_refused_before_writing(self, box, entries):
        root, outside, dl, server = box
        # the index declares the unzipped size of the SECOND spelling only, as
        # an attacker would to make the poisoned tree look installed
        blob = make_zip(entries)
        extra = {"unzipped_size": str(len(entries[-1][1]))}
        index_url = serve_packages(server, [("tiny", blob, extra)])
        result, output = run_download(index_url, dl, "tiny")
        assert result is False, output
        written = tree(str(dl / "corpora" / "tiny"))
        assert written == {}, written

    def test_a_huge_declared_member_is_refused_before_writing(self, box):
        root, outside, dl, server = box
        blob = make_zip([("tiny/a.txt", b"first"), ("tiny/big.bin", b"B" * 4096)])
        blob = patch_declared_size(blob, "tiny/big.bin", 0xFFFFFFF0)
        index_url = serve_packages(server, [("tiny", blob, {})])
        result, output = run_download(index_url, dl, "tiny")
        assert result is False
        assert not (dl / "corpora" / "tiny").exists()

    @needs_dir_fd
    def test_a_member_that_expands_past_its_declared_size_leaves_nothing(self, box):
        root, outside, dl, server = box
        blob = make_zip([("tiny/liar.bin", b"A" * 200_000)])
        blob = patch_declared_size(blob, "tiny/liar.bin", 1000)
        index_url = serve_packages(server, [("tiny", blob, {})])
        result, output = run_download(index_url, dl, "tiny")
        assert result is False
        leftover = dl / "corpora" / "tiny" / "liar.bin"
        assert not leftover.exists() or leftover.stat().st_size <= 1000
        assert not leftover.exists(), "a refused member left a partial file"

    def test_a_central_directory_bomb_is_refused_before_writing(self, box):
        root, outside, dl, server = box
        count = nltk.data.MAX_UNZIP_MEMBERS + 1
        entries = [("tiny/", b"")] + [(f"tiny/{i:06d}", b"") for i in range(count)]
        blob = make_zip(entries, compression=zipfile.ZIP_STORED)
        index_url = serve_packages(server, [("tiny", blob, {})])
        result, output = run_download(index_url, dl, "tiny")
        assert result is False
        assert not (dl / "corpora" / "tiny").exists()

    def test_an_aggregate_bomb_is_refused_before_writing(self, box):
        root, outside, dl, server = box
        zeros = bytes(16 * 1024 * 1024)
        blob = make_zip(
            [(f"tiny/z{i}.bin", zeros) for i in range(4)],
            compression=zipfile.ZIP_BZIP2,
        )
        index_url = serve_packages(server, [("tiny", blob, {})])
        result, output = run_download(index_url, dl, "tiny")
        assert result is False
        assert not (dl / "corpora" / "tiny").exists()

    def test_a_nested_zip_is_written_as_an_opaque_file(self, box):
        root, outside, dl, server = box
        inner = make_zip([("../../escape.txt", b"x"), ("/abs.txt", b"y")])
        result, output = install(
            server, dl, "tiny", [("tiny/", b""), ("tiny/inner.zip", inner)]
        )
        assert result is True, output
        placed = dl / "corpora" / "tiny" / "inner.zip"
        assert placed.read_bytes() == inner
        assert not (dl / "escape.txt").exists() and not (root / "escape.txt").exists()
        assert list(outside.iterdir()) == []

    def test_re_extraction_over_single_linked_files_still_works(self, box):
        root, outside, dl, server = box
        entries = [("tiny/", b""), ("tiny/words.txt", WORDS)]
        assert install(server, dl, "tiny", entries)[0] is True
        result, output = run_download(server.url("/index.xml"), dl, "tiny", force=True)
        assert result is True, output
        assert (dl / "corpora" / "tiny" / "words.txt").read_bytes() == WORDS

    def test_re_extraction_over_a_multiply_linked_file_is_refused(self, box):
        root, outside, dl, server = box
        entries = [("tiny/", b""), ("tiny/words.txt", WORDS)]
        assert install(server, dl, "tiny", entries)[0] is True
        secret = outside / "secret.txt"
        secret.write_bytes(WORDS)  # same size and bytes: the tree still looks installed
        placed = dl / "corpora" / "tiny" / "words.txt"
        placed.unlink()
        try:
            os.link(secret, placed)
        except OSError:
            pytest.skip("cannot hardlink across these directories")
        secret_before = secret.stat()
        result, output = run_download(server.url("/index.xml"), dl, "tiny", force=True)
        assert result is False
        assert secret.read_bytes() == WORDS
        assert secret.stat().st_mtime_ns == secret_before.st_mtime_ns

    @needs_symlink
    def test_stale_cleanup_does_not_follow_a_subdir_swapped_for_a_symlink(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        victim = outside / "victim.txt"
        victim.write_bytes(b"KEEP ME")
        entries = [("tiny/", b""), ("tiny/sub/", b""), ("tiny/sub/f.txt", b"f")]
        assert install(server, dl, "tiny", entries)[0] is True
        unzipdir = dl / "corpora" / "tiny"
        (unzipdir / "extra.txt").write_bytes(b"makes the install stale")
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        real_scandir = os.scandir
        state = {"armed": False, "calls": 0}

        def attacker_scandir(target=None):
            if state["armed"]:
                state["calls"] += 1
                if state["calls"] == 2:
                    # the attacker wins the window between listing and descent
                    os.rename(unzipdir / "sub", unzipdir / "sub_moved")
                    os.symlink(str(outside), str(unzipdir / "sub"))
            return real_scandir(target) if target is not None else real_scandir()

        monkeypatch.setattr(os, "scandir", attacker_scandir)
        for message in d._download_package(d.info("tiny"), str(dl), force=False):
            if isinstance(message, downloader.StaleMessage):
                state["armed"] = True
            elif isinstance(message, downloader.StartDownloadMessage):
                state["armed"] = False
        monkeypatch.setattr(os, "scandir", real_scandir)
        assert state["calls"] >= 2, "the cleanup never ran"
        assert victim.read_bytes() == b"KEEP ME"

    def test_a_dangling_symlink_in_an_install_is_stale_not_a_crash(self, box):
        root, outside, dl, server = box
        entries = [("tiny/", b""), ("tiny/words.txt", WORDS)]
        assert install(server, dl, "tiny", entries)[0] is True
        if not hasattr(os, "symlink"):
            pytest.skip("no symlinks")
        try:
            os.symlink(str(outside / "gone"), str(dl / "corpora" / "tiny" / "dangling"))
        except OSError:
            pytest.skip("cannot create symlinks here")
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        assert d.status("tiny", str(dl)) == d.STALE


class TestUnzipMore:
    @needs_dir_fd
    def test_a_hardlink_raced_in_after_the_downloader_check_is_refused(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        secret = outside / "secret.txt"
        secret.write_bytes(b"ORIGINAL")
        target = os.path.join(str(dl), "corpora", "tiny", "words.txt")
        real_lstat = os.lstat
        fired = []

        def attacker_lstat(path, *args, dir_fd=None, **kw):
            try:
                return real_lstat(path, *args, dir_fd=dir_fd, **kw)
            finally:
                # right after a by-name look at the target (the downloader's
                # own nlink check among them), before the extractor writes
                if dir_fd is None and str(path) == target and not fired:
                    fired.append(True)
                    with contextlib.suppress(OSError):
                        os.link(secret, target)

        blob = make_zip([("tiny/", b""), ("tiny/words.txt", b"EVILEVIL")])
        index_url = serve_packages(server, [("tiny", blob, {})])
        (dl / "corpora" / "tiny").mkdir(parents=True)
        monkeypatch.setattr(os, "lstat", attacker_lstat)
        result, output = run_download(index_url, dl, "tiny")
        monkeypatch.setattr(os, "lstat", real_lstat)
        if not fired or not os.path.exists(target):
            pytest.skip("the race window was not reached on this platform")
        assert result is False
        assert secret.read_bytes() == b"ORIGINAL"

    @needs_symlink
    def test_a_package_dir_planted_as_a_symlink_is_refused(self, box):
        root, outside, dl, server = box
        (dl / "corpora").mkdir()
        os.symlink(str(outside), str(dl / "corpora" / "tiny"))
        result, output = install(server, dl, "tiny", [("tiny/words.txt", WORDS)])
        assert result is False
        assert list(outside.iterdir()) == []

    def test_directories_differing_only_in_case_are_not_over_blocked(self, box):
        root, outside, dl, server = box
        result, output = install(
            server,
            dl,
            "tiny",
            [("tiny/", b""), ("tiny/A/x.txt", b"x"), ("tiny/a/y.txt", b"y")],
        )
        assert result is True, output


# ===========================================================================
# 5. pathsec.ZipFile directly: races, re-extraction, refused members
# ===========================================================================
@pytest.fixture
def zroot(pathsec_sandbox):
    root, outside = pathsec_sandbox
    dest = root / "dest"
    dest.mkdir()
    return root, outside, dest


def write_archive(path, entries):
    path.write_bytes(make_zip(entries))
    return str(path)


class TestPathsecZipFile:
    def test_re_extraction_replaces_a_single_linked_file(self, zroot):
        root, outside, dest = zroot
        archive = write_archive(root / "a.zip", [("p/f.txt", b"new")])
        (dest / "p").mkdir()
        (dest / "p" / "f.txt").write_bytes(b"old content")
        with pathsec.ZipFile(archive) as zf:
            zf.extract("p/f.txt", str(dest))
        assert (dest / "p" / "f.txt").read_bytes() == b"new"

    @needs_dir_fd
    def test_re_extraction_onto_a_multiply_linked_file_is_refused(self, zroot):
        root, outside, dest = zroot
        secret = outside / "secret"
        secret.write_bytes(b"ORIGINAL")
        archive = write_archive(root / "a.zip", [("p/f.txt", b"EVIL")])
        (dest / "p").mkdir()
        try:
            os.link(secret, dest / "p" / "f.txt")
        except OSError:
            pytest.skip("cannot hardlink across these directories")
        with pytest.raises((PermissionError, OSError)):
            with pathsec.ZipFile(archive) as zf:
                zf.extract("p/f.txt", str(dest))
        assert secret.read_bytes() == b"ORIGINAL"

    @pytest.mark.parametrize(
        "entries",
        [
            [("p/a", b"1"), ("p/a", b"2")],
            [("p/A", b"1"), ("p/a", b"2")],
            [("p/x/", b""), ("p/x", b"2")],
            [("p/x", b"1"), ("p/x/y", b"2")],
        ],
        ids=["duplicate", "case", "dir-file", "file-child"],
    )
    def test_member_by_member_extraction_still_sees_collisions(self, zroot, entries):
        root, outside, dest = zroot
        archive = write_archive(root / "c.zip", entries)
        with pytest.raises(ValueError, match=r"Security Violation \["):
            with pathsec.ZipFile(archive) as zf:
                for name in zf.namelist():
                    zf.extract(name, str(dest))
        assert tree(str(dest)) == {}

    def test_identical_directory_entries_are_not_a_collision(self, zroot):
        root, outside, dest = zroot
        archive = write_archive(
            root / "d.zip", [("p/", b""), ("p/", b""), ("p/f", b"x")]
        )
        with pathsec.ZipFile(archive) as zf:
            zf.extractall(str(dest))
        assert (dest / "p" / "f").read_bytes() == b"x"

    def test_a_refused_member_leaves_no_file(self, zroot):
        root, outside, dest = zroot
        blob = make_zip([("p/big.bin", b"B" * 4096)])
        (root / "b.zip").write_bytes(patch_declared_size(blob, "p/big.bin", 0xFFFFFFF0))
        with pytest.raises(ValueError):
            with pathsec.ZipFile(str(root / "b.zip")) as zf:
                zf.extract("p/big.bin", str(dest))
        assert not (dest / "p" / "big.bin").exists()

    @needs_dir_fd
    def test_a_member_failing_mid_copy_leaves_no_partial_file(self, zroot):
        root, outside, dest = zroot
        blob = make_zip([("p/liar.bin", b"A" * 200_000)])
        (root / "l.zip").write_bytes(patch_declared_size(blob, "p/liar.bin", 1000))
        with pytest.raises(zipfile.BadZipFile):
            with pathsec.ZipFile(str(root / "l.zip")) as zf:
                zf.extract("p/liar.bin", str(dest))
        assert not (dest / "p" / "liar.bin").exists()

    @needs_dir_fd
    def test_leaf_swapped_for_a_hardlink_after_lstat_is_not_written_through(
        self, zroot, monkeypatch
    ):
        root, outside, dest = zroot
        secret = outside / "secret"
        secret.write_bytes(b"ORIGINAL")
        archive = write_archive(root / "a.zip", [("p/f.txt", b"EVIL")])
        (dest / "p").mkdir()
        (dest / "p" / "f.txt").write_bytes(b"old")
        real_lstat = os.lstat
        fired = []

        def attacker_lstat(path, *args, dir_fd=None, **kw):
            result = real_lstat(path, *args, dir_fd=dir_fd, **kw)
            if dir_fd is not None and path == "f.txt" and not fired:
                fired.append(True)
                os.unlink(dest / "p" / "f.txt")
                os.link(secret, dest / "p" / "f.txt")
            return result

        monkeypatch.setattr(os, "lstat", attacker_lstat)
        try:
            with pathsec.ZipFile(archive) as zf:
                zf.extract("p/f.txt", str(dest))
        except (PermissionError, OSError):
            pass
        monkeypatch.setattr(os, "lstat", real_lstat)
        assert fired, "the race window was never reached"
        assert secret.read_bytes() == b"ORIGINAL"

    @needs_dir_fd
    def test_leaf_replanted_as_a_symlink_after_unlink_is_refused(
        self, zroot, monkeypatch
    ):
        root, outside, dest = zroot
        victim = outside / "victim"
        archive = write_archive(root / "a.zip", [("p/f.txt", b"EVIL")])
        (dest / "p").mkdir()
        (dest / "p" / "f.txt").write_bytes(b"old")
        real_unlink = os.unlink
        fired = []

        def attacker_unlink(path, *args, dir_fd=None, **kw):
            real_unlink(path, *args, dir_fd=dir_fd, **kw)
            if dir_fd is not None and path == "f.txt" and not fired:
                fired.append(True)
                os.symlink(str(victim), str(dest / "p" / "f.txt"))

        monkeypatch.setattr(os, "unlink", attacker_unlink)
        with pytest.raises(OSError):
            with pathsec.ZipFile(archive) as zf:
                zf.extract("p/f.txt", str(dest))
        monkeypatch.setattr(os, "unlink", real_unlink)
        assert fired and not victim.exists()

    @needs_dir_fd
    @pytest.mark.parametrize("member", ["p/sub/f.txt", "p/sub/deeper/"])
    def test_a_component_swapped_after_validation_is_not_followed(
        self, zroot, monkeypatch, member
    ):
        root, outside, dest = zroot
        archive = write_archive(
            root / "a.zip", [(member, b"" if member.endswith("/") else b"EVIL")]
        )
        (dest / "p" / "sub").mkdir(parents=True)
        real_validate = pathsec.validate_zip_archive
        fired = []

        def attacker_window(*args, **kw):
            result = real_validate(*args, **kw)
            if not fired:
                fired.append(True)
                os.rmdir(dest / "p" / "sub")
                os.symlink(str(outside), str(dest / "p" / "sub"))
            return result

        monkeypatch.setattr(pathsec, "validate_zip_archive", attacker_window)
        try:
            with pathsec.ZipFile(archive) as zf:
                zf.extract(member, str(dest))
        except OSError:
            pass
        assert fired
        assert list(outside.iterdir()) == [], list(outside.iterdir())

    def test_ordinary_archives_with_dirs_unicode_and_dotfiles_extract(self, zroot):
        root, outside, dest = zroot
        entries = [
            ("p/", b""),
            ("p/sub/", b""),
            ("p/sub/a.txt", b"a"),
            ("p/" + unicodedata.normalize("NFC", CAFE + ".txt"), b"c"),
            ("p/" + HANZI + ".txt", b"z"),
            ("p/with space.txt", b"s"),
            ("p/.hidden", b"h"),
            ("./", b""),
        ]
        archive = write_archive(root / "ok.zip", entries)
        with pathsec.ZipFile(archive) as zf:
            zf.extractall(str(dest))
            for name in zf.namelist():
                zf.extract(name, str(dest))  # and again, member by member
        assert (dest / "p" / "sub" / "a.txt").read_bytes() == b"a"
        assert (dest / "p" / (HANZI + ".txt")).read_bytes() == b"z"
        assert (dest / "p" / ".hidden").read_bytes() == b"h"


# ===========================================================================
# 6. It still works: a real install from the local server, loaded for real
# ===========================================================================
class TestStillWorks:
    def test_a_collection_installs_end_to_end_and_loads_through_nltk_data(
        self, box, monkeypatch
    ):
        from nltk.corpus.reader import WordListCorpusReader

        root, outside, dl, server = box
        words = make_zip(
            [
                ("tinywords/", b""),
                ("tinywords/en.txt", WORDS),
                ("tinywords/sub/", b""),
                ("tinywords/sub/fr.txt", (CAFE + "\n" + NAIVE + "\n").encode()),
                ("tinywords/README", b"a tiny corpus\n"),
            ]
        )
        grammar = make_zip(
            [("tinygrammar/", b""), ("tinygrammar/g.cfg", b"S -> 'a' S | 'a'\n")]
        )
        index_url = serve_packages(
            server,
            [
                ("tinywords", words, {}),
                ("tinygrammar", grammar, {"subdir": "grammars"}),
            ],
            collections=[("tinyall", ["tinywords", "tinygrammar"])],
        )
        result, output = run_download(index_url, dl, "tinyall")
        assert result is True, output
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        assert d.status("tinyall", str(dl)) == d.INSTALLED
        monkeypatch.setattr(nltk.data, "path", [str(dl)] + list(nltk.data.path))
        assert (
            nltk.data.load("corpora/tinywords/en.txt", format="text") == WORDS.decode()
        )
        reader = WordListCorpusReader(
            nltk.data.find("corpora/tinywords"), ["en.txt", "sub/fr.txt"]
        )
        assert reader.words("en.txt") == ["alpha", "beta", "gamma"]
        assert reader.words("sub/fr.txt") == [CAFE, NAIVE]
        grammar_obj = nltk.data.load("grammars/tinygrammar/g.cfg")
        assert str(grammar_obj.start()) == "S"
        # already installed, then forced over the existing single-linked files
        result, output = run_download(index_url, dl, "tinyall")
        assert result is True and "up-to-date" in output
        result, output = run_download(index_url, dl, "tinyall", force=True)
        assert result is True, output
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            d.list(download_dir=str(dl))
        assert_lines_clean(out.getvalue())
        assert "[*] tinywords" in out.getvalue()


def _network_available():
    try:
        socket.getaddrinfo("raw.githubusercontent.com", 443)
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _network_available(), reason="needs the network")
def test_real_nltk_download_of_a_small_package_still_works(tmp_path, monkeypatch):
    monkeypatch.setenv("NLTK_ALLOW_PROXIED_URLOPEN", "1")
    target = tmp_path / "nltk_data"
    d = downloader.Downloader(download_dir=str(target))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert d.download("mwa_ppdb", download_dir=str(target), quiet=True) is True
    assert d.status("mwa_ppdb", str(target)) == d.INSTALLED
    # the real index passes the structure ceilings with room to spare
    assert len(d._packages) > 100
    monkeypatch.setattr(nltk.data, "path", [str(target)] + list(nltk.data.path))
    path = nltk.data.find(
        "misc/mwa_ppdb/ppdb-1.0-xxxl-lexical.extended.synonyms.uniquepairs"
    )
    with pathsec.open(str(path), "rb") as handle:
        assert handle.read(100)
    listing = io.StringIO()
    with contextlib.redirect_stdout(listing):
        d.list(download_dir=str(target))
    assert_lines_clean(listing.getvalue())
    assert "[*] mwa_ppdb" in listing.getvalue()


class TestStatusRefusesPlantedEntries:
    """status() must report an install stale as soon as anything that is not a
    regular file or a directory is planted in its tree. The size sum alone
    misses a symlinked directory (never counted) and, on Windows, any link
    (lstat size 0), which is how the dangling-link check went green there."""

    def _tiny(self, box):
        root, outside, dl, server = box
        entries = [("tiny/", b""), ("tiny/words.txt", WORDS)]
        assert install(server, dl, "tiny", entries)[0] is True
        assert self._status(box) == downloader.Downloader.INSTALLED
        return dl / "corpora" / "tiny", outside

    @staticmethod
    def _status(box):
        # a fresh Downloader each time: status() caches per instance by design
        root, outside, dl, server = box
        d = downloader.Downloader(
            server_index_url=server.url("/index.xml"), download_dir=str(dl)
        )
        return d.status("tiny", str(dl))

    def test_a_symlinked_directory_inside_the_install_is_stale(self, box):
        tree, outside = self._tiny(box)
        if not hasattr(os, "symlink"):
            pytest.skip("no symlinks")
        try:
            os.symlink(str(outside), str(tree / "linkdir"), target_is_directory=True)
        except OSError:
            pytest.skip("cannot create symlinks here")
        assert self._status(box) == downloader.Downloader.STALE

    def test_a_symlinked_file_inside_the_install_is_stale(self, box):
        tree, outside = self._tiny(box)
        if not hasattr(os, "symlink"):
            pytest.skip("no symlinks")
        (outside / "real.txt").write_bytes(b"x")
        try:
            os.symlink(str(outside / "real.txt"), str(tree / "alias.txt"))
        except OSError:
            pytest.skip("cannot create symlinks here")
        assert self._status(box) == downloader.Downloader.STALE

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs are POSIX")
    def test_a_fifo_inside_the_install_is_stale(self, box):
        tree, _outside = self._tiny(box)
        os.mkfifo(str(tree / "pipe"))
        assert self._status(box) == downloader.Downloader.STALE

    def test_an_extra_regular_file_is_still_stale_by_size(self, box):
        tree, _outside = self._tiny(box)
        (tree / "extra.txt").write_bytes(b"more")
        assert self._status(box) == downloader.Downloader.STALE

    def test_an_empty_subdirectory_does_not_change_the_verdict(self, box):
        # a directory carries no size; a real install may hold one
        tree, _outside = self._tiny(box)
        (tree / "empty").mkdir()
        assert self._status(box) == downloader.Downloader.INSTALLED
