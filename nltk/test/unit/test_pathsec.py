import builtins
import io
import ipaddress
import os
import socket
import urllib.request
import zipfile
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

import nltk
import nltk.downloader  # We will inspect this module directly
from nltk import pathsec
from nltk.downloader import Downloader
from nltk.sem.util import read_sents


@pytest.fixture(autouse=True)
def enable_enforcement():
    """Dynamically toggle enforcement on for the duration of the tests."""
    original_enforce = pathsec.ENFORCE
    pathsec.ENFORCE = True
    yield
    pathsec.ENFORCE = original_enforce


# --- SSRF NETWORK TESTS ---


def test_valid_http_url():
    """Ensure valid URLs pass the SSRF filter without raising security exceptions."""
    try:
        pathsec.validate_network_url(
            "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/index.xml"
        )
    except (ValueError, PermissionError) as e:
        pytest.fail(f"Valid HTTP URL was incorrectly blocked by pathsec: {e}")


def test_ssrf_invalid_scheme():
    dl = Downloader(server_index_url="file:///etc/passwd")
    with pytest.raises((ValueError, PermissionError)):
        dl.index()


def test_ssrf_loopback_ip():
    dl = Downloader(server_index_url="http://127.0.0.1/admin")
    with pytest.raises((ValueError, PermissionError)):
        dl.index()


def test_ssrf_cloud_metadata_link_local():
    dl = Downloader(server_index_url="http://169.254.169.254/latest/meta-data/")
    with pytest.raises((ValueError, PermissionError)):
        dl.index()


def test_ssrf_ip_obfuscation():
    """Will FAIL on vulnerable branches (on Unix) because string-matching misses the decimal IP."""
    dl = Downloader(server_index_url="http://2852039166/latest/meta-data/")
    try:
        dl.index()
        pytest.fail("Request succeeded entirely, bypassing all filters.")
    except (ValueError, PermissionError):
        # SUCCESS (Your Branch): Our sentinel proactively blocked the restricted IP.
        pass
    except HTTPError as e:
        # FAILURE: The request bypassed local filters and hit the network layer!
        pytest.fail(f"Vulnerability bypassed localized string filters: {e}")
    except URLError as e:
        # SUCCESS (Windows only): DNS resolution strictly fails on decimal IPs natively.
        if isinstance(e.reason, socket.gaierror):
            pass
        else:
            pytest.fail(f"Unexpected network failure: {e}")


@pytest.mark.parametrize(
    "addr",
    [
        # direct internal IPv4
        "169.254.169.254",
        "127.0.0.1",
        # IPv4-mapped IPv6
        "::ffff:169.254.169.254",
        "::ffff:127.0.0.1",
        # NAT64 well-known prefix 64:ff9b::/96 embedding an internal IPv4
        "64:ff9b::a9fe:a9fe",  # -> 169.254.169.254
        "64:ff9b::7f00:1",  # -> 127.0.0.1
        # IPv4-compatible ::/96
        "::a9fe:a9fe",  # -> 169.254.169.254
        "::7f00:1",  # -> 127.0.0.1
        # 6to4 2002::/16 and Teredo 2001:0::/32 embedding an internal IPv4
        "2002:a9fe:a9fe::",  # 6to4 of 169.254.169.254
        "2001:0:0:0:0:0:a9fe:a9fe",  # Teredo with internal client
        # plain non-global IPv6
        "::1",
        "fe80::1",
        "fc00::1",
        "::",
    ],
)
def test_ip_filter_forbids_transition_embedded_internal(addr):
    """Internal IPv4 embedded in any IPv6->IPv4 transition form must be refused.

    Regression for the NAT64 / IPv4-compatible / 6to4 / Teredo SSRF bypass
    (CWE-918): the stdlib marks these wrappers globally routable, so the embedded
    IPv4 must be inspected.
    """
    assert pathsec._ip_is_forbidden(ipaddress.ip_address(addr)) is True


@pytest.mark.parametrize(
    "addr",
    [
        "8.8.8.8",
        "1.1.1.1",
        "::ffff:8.8.8.8",  # IPv4-mapped public
        "64:ff9b::808:808",  # NAT64 of the public 8.8.8.8
        "2606:4700:4700::1111",  # public IPv6 (Cloudflare)
        "2001:4860:4860::8888",  # public IPv6 (Google)
    ],
)
def test_ip_filter_allows_global(addr):
    """Genuinely globally-routable addresses (incl. NAT64-of-public) must pass."""
    assert pathsec._ip_is_forbidden(ipaddress.ip_address(addr)) is False


# --- PATH TRAVERSAL TESTS ---


def test_path_traversal_absolute():
    """
    Test if absolute paths bypass standard relative traversal checks.
    Will FAIL on vulnerable branches because standard builtins.open does not check path boundaries.
    """
    # Cross-platform absolute path guaranteed outside all allowed roots.
    # Linux/macOS: /_nltk_pathsec_test/secret.txt
    # Windows:     C:\_nltk_pathsec_test\secret.txt
    outside = os.path.join(os.path.abspath(os.sep), "_nltk_pathsec_test", "secret.txt")
    with pytest.raises((ValueError, PermissionError)):
        pathsec.open(outside, "r")


# --- ZIP-SLIP TESTS ---


def create_malicious_zip(filename):
    """Helper to create malicious zip files in memory."""
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w") as zf:
        zinfo = zipfile.ZipInfo(filename)
        zf.writestr(zinfo, b"malicious content")
    mem_zip.seek(0)
    return mem_zip


def test_zip_slip_traversal(tmp_path):
    """
    Test standard ../ Zip-Slip traversal.
    Will FAIL on vulnerable branches because standard zipfile silently sanitizes/ignores
    the traversal rather than proactively blocking it and raising an alert.
    """
    TargetZipFile = getattr(nltk.downloader, "ZipFile", zipfile.ZipFile)

    malicious_zip = create_malicious_zip("../../../evil.sh")
    with pytest.raises((ValueError, PermissionError)):
        with TargetZipFile(malicious_zip, "r") as zf:
            zf.extractall(tmp_path)


def test_zip_slip_absolute_path(tmp_path):
    """
    Test Zip-Slip using an absolute path.
    Will FAIL on vulnerable branches because standard zipfile silently ignores the absolute
    root rather than proactively raising a security alert.
    """
    TargetZipFile = getattr(nltk.downloader, "ZipFile", zipfile.ZipFile)

    malicious_zip = create_malicious_zip("/etc/cron.d/evil_cron")
    with pytest.raises((ValueError, PermissionError)):
        with TargetZipFile(malicious_zip, "r") as zf:
            zf.extractall(tmp_path)


def test_zip_slip_interior_dotdot(tmp_path):
    """Test an interior ``..`` member (validate/extract normalization mismatch).

    ``Path.resolve`` collapses the ``..`` so the member ``a/../b/evil.txt``
    validates as ``<root>/b/evil.txt`` (inside the root), but ``zipfile`` drops
    the ``..`` and writes ``<root>/a/b/evil.txt``. The hardened extractor must
    reject the interior-``..`` member outright rather than let the validated and
    written paths diverge (CWE-22).
    """
    malicious_zip = create_malicious_zip("a/../b/evil.txt")
    with pytest.raises((ValueError, PermissionError)):
        with pathsec.ZipFile(malicious_zip, "r") as zf:
            zf.extractall(tmp_path)


def test_zip_slip_interior_dotdot_symlink_escape(tmp_path):
    """An interior-``..`` member must not escape through an in-root symlink.

    With a pre-existing symlink at the path the dropped-``..`` member resolves
    to (``<root>/a/b`` -> outside), the old validator passed the member (it only
    inspected the ``..``-collapsed ``<root>/b/...``) while ``zipfile`` followed
    the symlink and wrote outside the root. The member must be rejected and
    nothing written outside the extraction root (CWE-22 / CWE-59).
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "extract"
    (root / "a").mkdir(parents=True)
    try:
        os.symlink(outside, root / "a" / "b")  # <root>/a/b -> outside
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported in this environment")

    malicious_zip = create_malicious_zip("a/../b/evil.txt")
    with pytest.raises((ValueError, PermissionError)):
        with pathsec.ZipFile(malicious_zip, "r") as zf:
            zf.extractall(root)
    assert not (
        outside / "evil.txt"
    ).exists(), "member escaped the extraction root via an in-root symlink"


# --- PROXY & HANDLER TESTS ---


def test_urlopen_honors_set_proxy_and_redirect_validation():
    """
    Regression test for Issue #3551.
    Ensures that pathsec.urlopen inherits global proxy configurations
    from urllib.request._opener, while still enforcing its own redirect validation.
    """
    test_proxy = "http://proxy.example.com:8080"

    # 1. Capture the pre-existing global state so we don't clobber it
    original_opener = urllib.request._opener

    # Setup: Directly inject a ProxyHandler into the global opener
    # to strictly test pathsec's inheritance, bypassing environment-dependent nltk.set_proxy behavior.
    proxy_handler = urllib.request.ProxyHandler({"http": test_proxy})
    global_opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(global_opener)

    try:
        captured_handlers = []

        def spy_build_opener(*handlers):
            captured_handlers.extend(handlers)
            return MagicMock()

        with patch("urllib.request.build_opener", side_effect=spy_build_opener):
            pathsec.urlopen("http://safe.example.com/data.zip")

        # 1. Verify ProxyHandler is present and contains our exact proxy
        proxy_handlers = [
            h for h in captured_handlers if isinstance(h, urllib.request.ProxyHandler)
        ]
        assert (
            len(proxy_handlers) == 1
        ), "ProxyHandler was not inherited by pathsec.urlopen"
        assert "http" in proxy_handlers[0].proxies
        assert proxy_handlers[0].proxies["http"] == test_proxy

        # 2. Verify _ValidatingRedirectHandler is present for SSRF protection
        redirect_handlers = [
            h
            for h in captured_handlers
            if isinstance(h, pathsec._ValidatingRedirectHandler)
        ]
        assert len(redirect_handlers) == 1, "_ValidatingRedirectHandler is missing"

        # 3. Verify the ProxyHandler was safely copied
        assert (
            proxy_handlers[0] is not proxy_handler
        ), "ProxyHandler instance was reused instead of copied! This breaks the global opener."

    finally:
        # Teardown: Safely restore the original global opener, leaving no trace of this test
        urllib.request.install_opener(original_opener)


def test_ssrf_dns_rebinding_blocked_at_connect(monkeypatch):
    """A hostname that resolves to a public IP at validation time but to a
    loopback IP at connect time (DNS rebinding) must still be blocked: the
    connection is pinned to the validated resolution.  Regression test for the
    validate-vs-connect DNS re-resolution TOCTOU in pathsec.urlopen.
    """
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    SECRET = b"LOOPBACK-ONLY-SECRET"

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(SECRET)

        def log_message(self, *args):
            pass

    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        host = "rebind.invalid.test"
        real_getaddrinfo = socket.getaddrinfo
        state = {"n": 0}

        def fake_getaddrinfo(h, p, *a, **k):
            if h == host:
                state["n"] += 1
                # 1st resolution (validation) -> public; later (connect) -> loopback
                ip = "93.184.216.34" if state["n"] == 1 else "127.0.0.1"
                return [
                    (
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        socket.IPPROTO_TCP,
                        "",
                        (ip, p if isinstance(p, int) else 0),
                    )
                ]
            return real_getaddrinfo(h, p, *a, **k)

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        # No proxy: force direct connection so the pinning handlers are used
        # regardless of the environment the test runs in.
        monkeypatch.setattr(urllib.request, "getproxies", lambda: {})

        leaked = None
        blocked = False
        try:
            resp = pathsec.urlopen(f"http://{host}:{port}/x")
            leaked = resp.read()
        except (PermissionError, URLError, ValueError):
            blocked = True

        assert blocked, "DNS-rebinding fetch was not blocked under ENFORCE=True"
        assert leaked != SECRET, "loopback secret was exfiltrated despite SSRF filter"
        assert state["n"] >= 2, "host was not re-resolved/validated at connect time"
    finally:
        srv.shutdown()


def _addrinfo(ip, port=80):
    return (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))


def test_pinned_connection_fails_closed_when_unresolved(monkeypatch):
    """If no validated address is available, _pinned_connection must NOT fall
    back to connecting by the raw hostname (which would re-resolve unvalidated
    and reopen the rebinding hole). It must fail closed."""
    monkeypatch.setattr(pathsec, "_resolve_and_validate_host", lambda h, p: [])

    attempted = []
    monkeypatch.setattr(
        socket, "create_connection", lambda addr, *a, **k: attempted.append(addr)
    )

    with pytest.raises(OSError):
        pathsec._pinned_connection("rebind.invalid.test", 80, None, None)
    assert not attempted, "must not connect by raw hostname when unresolved/unvalidated"


def test_pinned_connection_tries_all_validated_addresses(monkeypatch):
    """Pinning must still try every validated address in order, so a dual-stack
    host whose first (validated) address is unreachable still succeeds via a
    later validated address."""
    a1, a2 = _addrinfo("203.0.113.1"), _addrinfo("203.0.113.2")
    monkeypatch.setattr(pathsec, "_resolve_and_validate_host", lambda h, p: [a1, a2])

    sentinel = object()
    tried = []

    def fake_create_connection(addr, *a, **k):
        tried.append(addr[0])
        if addr[0] == "203.0.113.1":
            raise OSError("simulated unreachable first address")
        return sentinel

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    sock = pathsec._pinned_connection("dual.example.com", 80, None, None)
    assert sock is sentinel
    assert tried == ["203.0.113.1", "203.0.113.2"], "fallback across addresses lost"


def _capture_urlopen_handlers(monkeypatch, url="http://safe.example.com/x"):
    """Run pathsec.urlopen with build_opener stubbed out and return the handlers
    it was built with. No global opener, no DNS and no network I/O happen."""
    captured = []

    def spy_build_opener(*handlers):
        captured.extend(handlers)
        return MagicMock()

    monkeypatch.setattr(urllib.request, "_opener", None)
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    monkeypatch.setattr(urllib.request, "build_opener", spy_build_opener)
    pathsec.urlopen(url)
    return captured


def test_no_proxy_installs_pinning_and_disables_env_proxy(monkeypatch):
    """With no proxy in effect, the pinning handlers are installed and an
    explicit empty ProxyHandler is added so build_opener cannot silently
    re-enable environment proxies."""
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {})
    handlers = _capture_urlopen_handlers(monkeypatch)

    assert any(isinstance(h, pathsec._SafeHTTPHandler) for h in handlers)
    assert any(isinstance(h, pathsec._SafeHTTPSHandler) for h in handlers)
    proxy_handlers = [h for h in handlers if isinstance(h, urllib.request.ProxyHandler)]
    assert len(proxy_handlers) == 1 and proxy_handlers[0].proxies == {}


def test_env_proxy_skips_pinning_handlers(monkeypatch):
    """When environment proxies are set, the proxy is the egress: the pinning
    handlers must NOT be installed (they cannot do the CONNECT tunnel) and we
    must not force an empty ProxyHandler that would disable the env proxy."""
    monkeypatch.setattr(
        urllib.request, "getproxies", lambda: {"http": "http://proxy.local:3128"}
    )
    handlers = _capture_urlopen_handlers(monkeypatch)

    assert not any(isinstance(h, pathsec._SafeHTTPHandler) for h in handlers)
    assert not any(isinstance(h, pathsec._SafeHTTPSHandler) for h in handlers)
    # We did not append our own ProxyHandler({}); build_opener adds the env one.
    assert not any(isinstance(h, urllib.request.ProxyHandler) for h in handlers)


# --- SSRF address policy: "non-global is forbidden" + IPv4-mapped IPv6 ---------


@pytest.mark.parametrize(
    "addr",
    [
        "127.0.0.1",  # loopback
        "169.254.169.254",  # link-local (cloud metadata)
        "10.0.0.5",  # private
        "192.168.1.1",  # private
        "224.0.0.1",  # multicast (is_global is True on some CPython versions)
        "0.0.0.0",  # unspecified (routes to localhost on Linux)
        "100.64.1.1",  # carrier-grade NAT -- missed by the old explicit list
        "240.0.0.1",  # reserved
        "::1",  # IPv6 loopback
        "::",  # IPv6 unspecified
        "::ffff:127.0.0.1",  # IPv4-mapped loopback
        "::ffff:169.254.169.254",  # IPv4-mapped cloud metadata
        "::ffff:10.0.0.5",  # IPv4-mapped private
    ],
)
def test_ip_policy_forbids_non_global_and_mapped(addr):
    """Every non-global address -- including CGNAT/unspecified the old explicit
    list missed, and IPv4-mapped IPv6 forms -- must be rejected."""
    import ipaddress

    assert pathsec._ip_is_forbidden(ipaddress.ip_address(addr)), addr


@pytest.mark.parametrize("addr", ["8.8.8.8", "93.184.216.34", "2606:2800:220:1::1"])
def test_ip_policy_allows_global(addr):
    """Genuinely global addresses must still be allowed."""
    import ipaddress

    assert not pathsec._ip_is_forbidden(ipaddress.ip_address(addr)), addr


def test_resolve_and_validate_blocks_ipv4_mapped_loopback(monkeypatch):
    """Connect-side: a host resolving to an IPv4-mapped loopback IPv6 address
    must be blocked under ENFORCE (it would otherwise smuggle 127.0.0.1)."""
    mapped = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("::ffff:127.0.0.1", 80, 0, 0),
    )
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [mapped])
    with pytest.raises(PermissionError):
        pathsec._resolve_and_validate_host("mapped.invalid.test", 80)


def test_validate_network_url_blocks_cgnat(monkeypatch):
    """Validation-side: carrier-grade NAT (100.64.0.0/10) is non-global and must
    now be rejected, where the old explicit list let it through."""
    monkeypatch.setattr(
        pathsec, "_resolve_hostname", lambda h: [_addrinfo("100.64.1.1")]
    )
    with pytest.raises((PermissionError, ValueError)):
        pathsec.validate_network_url("http://cgnat.invalid.test/x", context="test")


def test_streambackedcorpusview_string_fileid_uses_pathsec(tmp_path, monkeypatch):
    from pathlib import Path

    from nltk.corpus.reader.util import StreamBackedCorpusView

    blocked_file = tmp_path / "secret.txt"
    blocked_file.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: set())
    monkeypatch.setattr(os, "getcwd", lambda: str(Path(tmp_path).parent / "elsewhere"))

    view = StreamBackedCorpusView(str(blocked_file), block_reader=lambda stream: [])

    with pytest.raises((ValueError, PermissionError)):
        view._open()


def test_read_sents_enforces_pathsec():
    # 1. Enable strict sandbox
    pathsec.ENFORCE = True

    # 2. Construct an absolute path that is structurally impossible to be a valid NLTK data root
    # Using a root-level path like '/nonexistent_nltk_root/file.txt' ensures it
    # cannot be in the allowed_roots list, avoiding the need for mocks.
    forbidden_path = os.path.join(os.sep, "nonexistent_nltk_root_XYZ_123", "secret.txt")

    # 3. Verify that attempting to read this file triggers a PermissionError
    # We catch the exception to verify it's the right type.
    # If the function succeeds (no exception), the test fails.
    with pytest.raises(PermissionError, match="Security Violation"):
        read_sents(forbidden_path)


# ----------------------------------------------------------------------
# Malicious Subclasses for Type Confusion & Object Manipulation Tests
# ----------------------------------------------------------------------


class ZeroLengthStr(str):
    """
    Simulates a boolean discrepancy attack.
    Overrides __len__ so that `if not path:` evaluates to True,
    attempting to bypass permissive guards while tricking the C-API.
    """

    def __len__(self):
        return 0


class DualFacedPath(os.PathLike):
    """
    Simulates an interface discrepancy (desync) attack.
    Presents a safe path to `str()` casting, but delivers a malicious
    path when `os.fspath()` is invoked by low-level file operations.
    """

    def __init__(self, real_path, shown_path):
        self.real_path = str(real_path)
        self.shown = str(shown_path)

    def __fspath__(self):
        return self.real_path

    def __str__(self):
        return self.shown


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def sandbox_env(tmp_path):
    """Sets up a mock allowed root and an outside unallowed directory."""
    safe_dir = tmp_path / "nltk_safe_root"
    safe_dir.mkdir()

    unsafe_dir = tmp_path / "outside_root"
    unsafe_dir.mkdir()

    secret_file = unsafe_dir / "secret.txt"
    secret_file.write_text("UNAUTHORIZED_DATA", encoding="utf-8")

    allowed_file = safe_dir / "allowed.txt"
    allowed_file.write_text("AUTHORIZED_DATA", encoding="utf-8")

    archive_path = unsafe_dir / "unauthorized.zip"
    archive_path.touch()

    return safe_dir, unsafe_dir, secret_file, allowed_file, archive_path


# ----------------------------------------------------------------------
# Restrictive Guard Tests
# ----------------------------------------------------------------------


def test_restrictive_guard_blocks_boolean_discrepancy_open(sandbox_env):
    """Ensures restrictive type enforcement blocks length-override bypasses in open()."""
    safe_dir, _, secret_file, _, _ = sandbox_env

    malicious_path = ZeroLengthStr(str(secret_file))

    # The strict policy must reject the subclass completely
    with pytest.raises(
        TypeError,
        match="Strict security policy: Path must resolve to exact str or bytes",
    ):
        pathsec.open(malicious_path, "r", required_root=safe_dir)


def test_restrictive_guard_blocks_interface_desync_open(sandbox_env):
    """Ensures the real path is extracted and evaluated, catching the root escape."""
    safe_dir, _, secret_file, allowed_file, _ = sandbox_env

    malicious_path = DualFacedPath(real_path=secret_file, shown_path=allowed_file)

    # The guard extracts real_path via os.fspath(), bypassing the __str__ illusion.
    # validate_path then correctly identifies it as a root escape and throws ValueError.
    with pytest.raises(ValueError, match="Security Violation .* escapes root"):
        pathsec.open(malicious_path, "r", required_root=safe_dir)


def test_restrictive_guard_blocks_boolean_discrepancy_zipfile(sandbox_env):
    """Ensures restrictive type enforcement blocks length-override bypasses in ZipFile()."""
    _, _, _, _, archive_path = sandbox_env

    malicious_path = ZeroLengthStr(str(archive_path))

    # ZipFile path normalization must also catch and reject the subclass
    with pytest.raises(
        TypeError,
        match="Strict security policy: Path must resolve to exact str or bytes",
    ):
        pathsec.ZipFile(malicious_path, "r")


def test_restrictive_guard_blocks_interface_desync_zipfile(sandbox_env):
    """Ensures the real path is extracted and evaluated by ZipFile."""
    safe_dir, _, _, allowed_file, archive_path = sandbox_env

    # To strictly prove the desync fails validation regardless of the /tmp/ environment,
    # we point the underlying real_path to an explicitly forbidden global location.
    forbidden_path = "/this_is_a_forbidden_path_12345/unauth.zip"
    malicious_path = DualFacedPath(real_path=forbidden_path, shown_path=allowed_file)

    # The pathsec guard extracts the forbidden path and validate_path correctly
    # blocks it, raising a PermissionError before it ever reaches zipfile.ZipFile.
    with pytest.raises(PermissionError, match="Security Violation"):
        pathsec.ZipFile(malicious_path, "r")


def test_restrictive_guard_allows_pure_primitives(sandbox_env):
    """Ensures pure primitive strings, pathlib.Path objects, and bytes still function normally."""
    safe_dir, _, _, allowed_file, _ = sandbox_env

    # pathlib.Path should be allowed
    with pathsec.open(allowed_file, "r", required_root=safe_dir) as f:
        assert f.read() == "AUTHORIZED_DATA"

    # Pure string should be allowed
    with pathsec.open(str(allowed_file), "r", required_root=safe_dir) as f:
        assert f.read() == "AUTHORIZED_DATA"

    # Bytes path should be allowed (decoded safely)
    with pathsec.open(os.fsencode(str(allowed_file)), "r", required_root=safe_dir) as f:
        assert f.read() == "AUTHORIZED_DATA"
