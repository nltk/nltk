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


# SSRF NETWORK TESTS
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


# PATH TRAVERSAL TESTS
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


# ALLOWED-ROOTS / TEMP-DIR FALLBACK TESTS
def test_get_allowed_roots_survives_missing_tempdir(tmp_path, monkeypatch):
    """Regression test for issue #3716.

    ``_get_allowed_roots()`` used to build its fallback-location list as a
    literal ``[..., tempfile.gettempdir()]``, which evaluates
    ``tempfile.gettempdir()`` while constructing the list; *before* the
    loop's ``try/except`` runs. On a system with no usable temp directory
    (read-only root filesystem, nothing mounted at ``/tmp``), ``gettempdir()``
    raises ``FileNotFoundError`` (an ``OSError`` subclass) that propagates out
    of the whole function, discarding the roots already collected from
    ``nltk.data.path``/``NLTK_DATA`` and breaking resource lookups (e.g.
    ``sent_tokenize()``) even when the resource is already cached.
    """
    import nltk.data

    known_root = tmp_path / "nltk_data_known_root"
    known_root.mkdir()

    monkeypatch.setattr(nltk.data, "path", nltk.data.path + [str(known_root)])

    # Force a clean cache: _get_allowed_roots() memoizes on (data.path, NLTK_DATA).
    pathsec._ALLOWED_ROOTS_CACHE = None
    pathsec._LAST_DATA_PATHS = None

    with patch("tempfile.gettempdir", side_effect=FileNotFoundError("no temp dir")):
        roots = pathsec._get_allowed_roots()

    assert known_root.resolve() in roots


# ZIP-SLIP TESTS
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


# PROXY & HANDLER TESTS
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

    # Proxied fetches fail closed by default now (GHSA-6ww7, CWE-918). This test
    # exercises the proxy *inheritance/copy* behavior, so opt into trusting the
    # proxy for its duration.
    original_allow = pathsec.ALLOW_PROXIED_FETCH
    pathsec.ALLOW_PROXIED_FETCH = True

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
        pathsec.ALLOW_PROXIED_FETCH = original_allow
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


def test_env_proxy_fails_closed_under_enforce(monkeypatch):
    """A configured proxy is the egress, so NLTK cannot pin the validated IP and
    its SSRF filter no longer governs the destination (GHSA-6ww7, CWE-918).
    Under ENFORCE the proxied fetch must fail closed, not silently proceed."""
    monkeypatch.setattr(
        urllib.request, "getproxies", lambda: {"http": "http://proxy.local:3128"}
    )
    monkeypatch.setattr(urllib.request, "_opener", None)
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", False)

    with pytest.raises(PermissionError, match="proxied fetch"):
        pathsec.urlopen("http://safe.example.com/x")


# issue #3748: NO_PROXY must not be mistaken for a configured proxy
#
# getproxies() reports a "no" key for NO_PROXY, an exclusion list. The old check
# treated any non-empty getproxies() as a proxy and blocked every download. The
# fix keys on real http/https schemes and defers the host decision to
# proxy_bypass; so NO_PROXY-only is direct+pinned (benign), while a genuine
# proxy egress stays blocked (GHSA-6ww7). These pin both halves.


def test_no_proxy_only_is_not_treated_as_proxied(monkeypatch):
    """NO_PROXY alone (getproxies()=={'no': ...}) is a bypass list, not a proxy.

    The fetch must go direct and pinned, exactly as if nothing were set;
    otherwise every download fails in any environment that sets NO_PROXY.
    """
    monkeypatch.setattr(
        urllib.request, "getproxies", lambda: {"no": "localhost,127.0.0.1"}
    )
    handlers = _capture_urlopen_handlers(monkeypatch)

    assert any(isinstance(h, pathsec._SafeHTTPHandler) for h in handlers)
    assert any(isinstance(h, pathsec._SafeHTTPSHandler) for h in handlers)
    proxy_handlers = [h for h in handlers if isinstance(h, urllib.request.ProxyHandler)]
    assert len(proxy_handlers) == 1 and proxy_handlers[0].proxies == {}


@pytest.mark.parametrize(
    "proxies, bypass, expected",
    [
        # benign: no real http/https proxy would carry the request
        ({}, False, False),  # nothing set
        ({"no": "localhost"}, False, False),  # NO_PROXY only (the reported bug)
        ({"no": "*"}, False, False),  # NO_PROXY wildcard
        ({"all": "http://p:8080"}, False, False),  # urllib ignores 'all' for http/https
        ({"ftp": "http://p:8080"}, False, False),  # only an ftp proxy
        ({"http": "http://p:8080"}, True, False),  # http proxy but host bypassed
        ({"https": "http://p:8080"}, True, False),  # https proxy but host bypassed
        ({"http": "http://p:8080", "no": "raw.githubusercontent.com"}, True, False),
        # must block: a real http/https proxy carries the host
        ({"http": "http://p:8080"}, False, True),
        ({"https": "http://p:8080"}, False, True),
        ({"http": "http://p:8080", "https": "http://p:8080"}, False, True),
        ({"http": "http://p:8080", "no": "otherhost.example"}, False, True),
    ],
)
def test_env_proxy_carries_truth_table(proxies, bypass, expected):
    """_env_proxy_carries mirrors urllib: proxied iff a real http/https proxy
    would carry the host and it is not bypassed by NO_PROXY. Fails closed."""
    with patch.object(urllib.request, "getproxies", lambda: proxies), patch.object(
        urllib.request, "proxy_bypass", lambda host: bypass
    ):
        assert (
            pathsec._env_proxy_carries("http://raw.githubusercontent.com/x") is expected
        )


def test_issue_3748_no_proxy_env_downloads_are_not_blocked(monkeypatch):
    """The reporter's exact scenario, end to end through real getproxies().

    Only NO_PROXY is set (no HTTP_PROXY/HTTPS_PROXY), so getproxies() returns
    {'no': ...} from the environment and nothing is proxied; the download must
    install the pinning handlers and proceed, not raise 'proxied fetch'.
    """
    for var in (
        "HTTP_PROXY",
        "http_proxy",
        "HTTPS_PROXY",
        "https_proxy",
        "ALL_PROXY",
        "all_proxy",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")

    assert urllib.request.getproxies().get("no")  # sanity: the env is as reported
    handlers = _capture_urlopen_handlers(monkeypatch)
    assert any(isinstance(h, pathsec._SafeHTTPSHandler) for h in handlers)
    proxy_handlers = [h for h in handlers if isinstance(h, urllib.request.ProxyHandler)]
    assert len(proxy_handlers) == 1 and proxy_handlers[0].proxies == {}


@pytest.mark.parametrize(
    "target",
    [
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://127.0.0.1/admin",  # loopback
        "http://[::1]/admin",  # loopback IPv6
        "http://10.0.0.1/internal",  # RFC1918
        "http://metadata.google.internal/computeMetadata/v1/",  # metadata by name
        "http://example.com/x",  # even an innocuous host: proxy = unpinnable
    ],
)
def test_proxied_fetch_refused_for_every_target_even_with_no_proxy_present(
    target, monkeypatch
):
    """Exploit must not leak: when a real proxy carries the request, NLTK cannot
    pin the IP, so every target is refused (GHSA-6ww7); including when NO_PROXY
    is set for *other* hosts, so the fix cannot be turned into a bypass."""
    monkeypatch.setattr(
        urllib.request,
        "getproxies",
        lambda: {
            "http": "http://proxy.local:3128",
            "https": "http://proxy.local:3128",
            "no": "trusted.internal",
        },
    )
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda host: False)
    monkeypatch.setattr(urllib.request, "_opener", None)
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", False)

    with pytest.raises(PermissionError, match="proxied fetch"):
        pathsec.urlopen(target)


def test_proxy_with_no_proxy_target_still_pins(monkeypatch):
    """A proxy is configured but the target is in NO_PROXY: urllib fetches it
    directly, so NLTK must pin (not block); and the SSRF filter still governs
    the direct connection."""
    monkeypatch.setattr(
        urllib.request,
        "getproxies",
        lambda: {"http": "http://proxy.local:3128", "no": "raw.githubusercontent.com"},
    )
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda host: True)
    handlers = _capture_urlopen_handlers(
        monkeypatch, url="http://raw.githubusercontent.com/x"
    )

    assert any(isinstance(h, pathsec._SafeHTTPSHandler) for h in handlers)
    proxy_handlers = [h for h in handlers if isinstance(h, urllib.request.ProxyHandler)]
    assert len(proxy_handlers) == 1 and proxy_handlers[0].proxies == {}


def test_proxy_with_unbypassed_target_still_fails_closed(monkeypatch):
    """The attack the fix must NOT reopen: a real proxy carries the target (not
    bypassed), so NLTK cannot pin the IP; the fetch must still be refused even
    though NO_PROXY is present for *other* hosts (GHSA-6ww7)."""
    monkeypatch.setattr(
        urllib.request,
        "getproxies",
        lambda: {"http": "http://proxy.local:3128", "no": "example.com"},
    )
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda host: False)
    monkeypatch.setattr(urllib.request, "_opener", None)
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", False)

    with pytest.raises(PermissionError, match="proxied fetch"):
        pathsec.urlopen("http://raw.githubusercontent.com/x")


def test_env_proxy_opt_in_skips_pinning_handlers(monkeypatch):
    """When the operator opts into trusting the proxy, the proxy is the egress:
    the pinning handlers must NOT be installed (they cannot do the CONNECT
    tunnel) and we must not force an empty ProxyHandler that disables the env
    proxy. Gated behind the explicit opt-in that fail-closed now requires."""
    monkeypatch.setattr(
        urllib.request, "getproxies", lambda: {"http": "http://proxy.local:3128"}
    )
    monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", True)
    handlers = _capture_urlopen_handlers(monkeypatch)

    assert not any(isinstance(h, pathsec._SafeHTTPHandler) for h in handlers)
    assert not any(isinstance(h, pathsec._SafeHTTPSHandler) for h in handlers)
    # We did not append our own ProxyHandler({}); build_opener adds the env one.
    assert not any(isinstance(h, urllib.request.ProxyHandler) for h in handlers)


def test_proxied_fetch_does_not_reach_internal_target(monkeypatch):
    """End-to-end regression for GHSA-6ww7: a proxy whose egress is a
    loopback/internal service must not be reachable through pathsec.urlopen even
    when the requested URL validates as a public destination. Fail closed by
    default; only the explicit opt-in lets the (trusted-proxy) fetch through."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    SECRET = b"INTERNAL-ONLY-SECRET"

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(SECRET)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)  # loopback == "internal"
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        # A configured proxy whose egress is the internal loopback service.
        monkeypatch.setattr(
            urllib.request, "getproxies", lambda: {"http": f"http://127.0.0.1:{port}"}
        )
        monkeypatch.setattr(urllib.request, "_opener", None)
        public_url = "http://93.184.216.34/"  # validates as a public destination

        # Default: fail closed; the internal secret is NOT fetched.
        monkeypatch.setattr(pathsec, "ENFORCE", True)
        monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", False)
        with pytest.raises(PermissionError, match="proxied fetch"):
            pathsec.urlopen(public_url, timeout=5)

        # Opt-in: the trusted-proxy fetch is allowed to proceed.
        monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", True)
        body = pathsec.urlopen(public_url, timeout=5).read()
        assert body == SECRET
    finally:
        server.shutdown()


# SSRF address policy: "non-global is forbidden" + IPv4-mapped IPv6
@pytest.mark.parametrize(
    "addr",
    [
        "127.0.0.1",  # loopback
        "169.254.169.254",  # link-local (cloud metadata)
        "10.0.0.5",  # private
        "192.168.1.1",  # private
        "224.0.0.1",  # multicast (is_global is True on some CPython versions)
        "0.0.0.0",  # unspecified (routes to localhost on Linux)
        "100.64.1.1",  # carrier-grade NAT; missed by the old explicit list
        "240.0.0.1",  # reserved
        "::1",  # IPv6 loopback
        "::",  # IPv6 unspecified
        "::ffff:127.0.0.1",  # IPv4-mapped loopback
        "::ffff:169.254.169.254",  # IPv4-mapped cloud metadata
        "::ffff:10.0.0.5",  # IPv4-mapped private
    ],
)
def test_ip_policy_forbids_non_global_and_mapped(addr):
    """Every non-global address; including CGNAT/unspecified the old explicit
    list missed, and IPv4-mapped IPv6 forms; must be rejected."""
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


# Malicious Subclasses for Type Confusion & Object Manipulation Tests


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


# Fixtures


@pytest.fixture
def sandbox_env(tmp_path, monkeypatch):
    """Sets up a mock allowed root and an outside unallowed directory."""
    safe_dir = tmp_path / "nltk_safe_root"
    safe_dir.mkdir()

    # Register the mock allowed root on nltk.data.path so it is a genuine
    # pathsec-allowed root. (This previously relied on the whole system temp
    # directory being blanket-allowed, which it no longer is.)
    import nltk.data as _nltk_data

    monkeypatch.setattr(_nltk_data, "path", [str(safe_dir), *_nltk_data.path])

    unsafe_dir = tmp_path / "outside_root"
    unsafe_dir.mkdir()

    secret_file = unsafe_dir / "secret.txt"
    secret_file.write_text("UNAUTHORIZED_DATA", encoding="utf-8")

    allowed_file = safe_dir / "allowed.txt"
    allowed_file.write_text("AUTHORIZED_DATA", encoding="utf-8")

    archive_path = unsafe_dir / "unauthorized.zip"
    archive_path.touch()

    return safe_dir, unsafe_dir, secret_file, allowed_file, archive_path


# Restrictive Guard Tests


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


# System temp dir: trust only a PRIVATE per-user temp, never a shared
# world-writable one (GHSA-p4rw follow-up, CWE-377/CWE-378)

posix_only = pytest.mark.skipif(
    os.name != "posix", reason="POSIX ownership/permission semantics"
)


@posix_only
def test_is_private_dir_distinguishes_world_and_group_writable(tmp_path):
    """is_private_dir accepts a user-owned, non-shared dir and rejects world- or
    group-writable ones (and missing paths)."""
    priv = tmp_path / "priv"
    priv.mkdir()
    os.chmod(priv, 0o700)
    world = tmp_path / "world"
    world.mkdir()
    os.chmod(world, 0o777)
    group = tmp_path / "group"
    group.mkdir()
    os.chmod(group, 0o770)

    assert pathsec.is_private_dir(str(priv)) is True
    assert pathsec.is_private_dir(str(world)) is False
    assert pathsec.is_private_dir(str(group)) is False
    assert pathsec.is_private_dir(str(tmp_path / "missing")) is False


@posix_only
def test_world_writable_temp_dir_is_not_trusted_and_is_refused(tmp_path, monkeypatch):
    """A shared world-writable temp dir (like Linux /tmp) must not be an allowed
    root, and a file there is refused under ENFORCE."""
    from pathlib import Path

    import nltk.data as _nltk_data

    shared = tmp_path / "shared_tmp"
    shared.mkdir()
    os.chmod(shared, 0o777)

    monkeypatch.setattr(pathsec, "ENFORCE", True)
    # Isolate the allowed roots: no data paths, so the only candidate is the
    # (world-writable) temp dir under test; which must be rejected.
    monkeypatch.setattr(_nltk_data, "path", [])
    monkeypatch.setenv("NLTK_DATA", "")
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(shared))
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None)

    allowed = pathsec._get_allowed_roots()
    assert Path(shared).resolve() not in allowed

    secret = shared / "secret.txt"
    secret.write_text("SECRET", encoding="utf-8")
    with pytest.raises((PermissionError, ValueError)):
        with pathsec.open(str(secret), "r"):
            pass


def test_private_temp_dir_trust_matches_its_privacy(monkeypatch):
    """The real system temp dir is trusted iff it is private (macOS $TMPDIR /
    Windows %TEMP% are private and trusted; a world-writable Linux /tmp is not)."""
    import tempfile
    from pathlib import Path

    import nltk.data as _nltk_data

    # Isolate from data paths / the conftest base registration so we observe the
    # temp dir's own trust decision.
    monkeypatch.setattr(_nltk_data, "path", [])
    monkeypatch.setenv("NLTK_DATA", "")
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None)

    tmp = Path(tempfile.gettempdir()).resolve()
    roots = pathsec._get_allowed_roots()
    if pathsec.is_private_dir(str(tmp)):
        assert tmp in roots
    else:
        assert tmp not in roots


@posix_only
def test_authorize_data_dir_refuses_world_writable(tmp_path, monkeypatch):
    """A world-writable download_dir is refused (not registered) with a warning:
    another local user could plant files there (the download_dir threat)."""
    import nltk.data as _nltk_data
    from nltk.downloader import _authorize_data_dir

    monkeypatch.setattr(_nltk_data, "path", list(_nltk_data.path))
    shared = tmp_path / "ww_download"
    shared.mkdir()
    os.chmod(shared, 0o777)
    real = os.path.realpath(str(shared))

    with pytest.warns(UserWarning, match="non-private"):
        _authorize_data_dir(str(shared))
    assert real not in {
        os.path.realpath(str(p)) for p in _nltk_data.path if isinstance(p, str)
    }


def test_authorize_data_dir_registers_private_dir(tmp_path, monkeypatch):
    """A private download_dir is authorized as its own allowed root."""
    import nltk.data as _nltk_data
    from nltk.downloader import _authorize_data_dir

    monkeypatch.setattr(_nltk_data, "path", list(_nltk_data.path))
    custom = tmp_path / "mydata"
    custom.mkdir()
    os.chmod(custom, 0o700)
    real = os.path.realpath(str(custom))

    def registered():
        return real in {
            os.path.realpath(str(p)) for p in _nltk_data.path if isinstance(p, str)
        }

    assert not registered()
    _authorize_data_dir(str(custom))
    assert registered()


class TestUrlSchemePathBypass:
    """GHSA-8mgp-746c-j5xp: validate_path() must not authorize URL-shaped paths.

    The old check did ``if "://" in raw: return``; unconditional authorization
    for anything with an http/https/ftp scheme. To the kernel ``http://../x`` is
    the directory ``http:`` then ``..``, so this waved a traversal straight
    through every allowed root and defeated every downstream path check.
    """

    @pytest.mark.parametrize(
        "path",
        [
            "http://../../../../etc/passwd",
            "https://../../x",
            "ftp://../../y",
            "HTTP://../../etc/passwd",  # case
            "  https://../../etc/passwd",  # leading whitespace
        ],
    )
    def test_url_prefix_is_not_an_authorization_bypass(self, path):
        # The single most important regression: if this ever passes silently,
        # GHSA-8mgp is back.
        with pytest.raises(PermissionError):
            pathsec.validate_path(path)

    @pytest.mark.parametrize(
        "path",
        [
            "file:///tmp/x?y/../../etc/passwd",  # query
            "file:///etc/passwd#frag",  # fragment
            "file:///tmp/x;/../../etc/passwd",  # params
        ],
    )
    def test_ambiguous_file_url_is_rejected(self, path):
        # urllib opens Request.selector (keeps ?/#/;), urlparse().path drops them,
        # so a file: URL with those would validate a different target than opens.
        with pytest.raises(PermissionError):
            pathsec.validate_path(path)

    def test_plain_in_root_path_still_validates(self, tmp_path, monkeypatch):
        # No false positive: a normal filesystem path inside an allowed root must
        # still pass after the URL rejection is added.
        import nltk.data as _nltk_data

        root = tmp_path / "nltk_data"
        (root / "corpora").mkdir(parents=True)
        monkeypatch.setattr(_nltk_data, "path", [str(root)])
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        pathsec.validate_path(str(root / "corpora" / "x.txt"))  # must not raise


class TestModelArtifactSaveContainment:
    """GHSA-8mgp: low-level model save/load must not open outside allowed roots."""

    def test_averaged_perceptron_save_load_refuse_outside_root(
        self, tmp_path, monkeypatch
    ):
        import pathlib
        import shutil

        import nltk.data as _nltk_data
        from nltk.tag.perceptron import AveragedPerceptron

        sandbox = tmp_path / "nltk_data"
        sandbox.mkdir()
        # A genuinely-outside target: a fresh $HOME dir. NOT tmp_path; the
        # private system temp is an allowed pathsec root on macOS, so a temp
        # target would not actually be outside the sandbox.
        outside_dir = pathlib.Path.home() / (".ghsa8mgp_pathsec_test_%s" % os.getpid())
        outside = outside_dir / "model.json"
        monkeypatch.setattr(_nltk_data, "path", [str(sandbox)])
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        outside_dir.mkdir(exist_ok=True)
        try:
            # Guard the test: the target must be genuinely outside the sandbox.
            with pytest.raises(PermissionError):
                with pathsec.open(str(outside), "w"):
                    pass

            ap = AveragedPerceptron()
            ap.weights = {"f": {"t": 1.0}}
            with pytest.raises(PermissionError):
                ap.save(str(outside))
            assert not outside.exists(), "refused save must not have written the file"
            with pytest.raises(PermissionError):
                ap.load(str(outside))
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_save_to_json_refuses_outside_loc_without_widening_sandbox(
        self, tmp_path, monkeypatch
    ):
        import pathlib
        import shutil

        import nltk.data as _nltk_data
        from nltk.tag.perceptron import PerceptronTagger

        sandbox = tmp_path / "nltk_data"
        sandbox.mkdir()
        outside_dir = pathlib.Path.home() / (".ghsa8mgp_savejson_test_%s" % os.getpid())
        monkeypatch.setattr(_nltk_data, "path", [str(sandbox)])
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        shutil.rmtree(outside_dir, ignore_errors=True)
        try:
            tagger = PerceptronTagger(load=False)
            tagger.model.weights = {"f": {"t": 1.0}}
            tagger.tagdict = {}
            tagger.classes = {"t"}

            with pytest.raises(PermissionError):
                tagger.save_to_json(lang="xxx", loc=str(outside_dir))
            # Refused up front: neither written nor added to the allow-list.
            assert not outside_dir.exists(), "refused save_to_json created the dir"
            authorized = {
                os.path.realpath(str(p)) for p in _nltk_data.path if isinstance(p, str)
            }
            assert os.path.realpath(str(outside_dir)) not in authorized
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)


class TestStagingUnderDataRoot:
    """``nltk.data.make_staging_dir`` stages NLTK's own output inside a data root,
    so the default save destination is within the pathsec sandbox on every
    platform (including Linux, where the shared ``/tmp`` is not a root). When no
    data root is writable it refuses rather than falling back to an untrusted
    temp dir, forcing the caller to pass an explicit destination.
    """

    def test_staging_dir_is_inside_a_data_root_and_passes_sandbox(
        self, tmp_path, monkeypatch
    ):
        """The staged dir is created under a data root, is private (0700), and its
        contents pass validate_path without any temp-dir trust."""
        import nltk.data as _data

        root = tmp_path / "nltk_data"
        root.mkdir()
        monkeypatch.setattr(_data, "path", [str(root)])
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None

        d = _data.make_staging_dir(prefix="nltk_probe_")
        assert os.path.realpath(d).startswith(os.path.realpath(str(root)))
        assert pathsec.is_private_dir(d)
        pathsec.validate_path(os.path.join(d, "out.tab"), context="test")

    def test_refuses_when_no_writable_data_root(self, tmp_path, monkeypatch):
        """With no writable data root, staging refuses (PermissionError) instead of
        writing to an out-of-sandbox temp dir."""
        import nltk.data as _data

        blocker = tmp_path / "not_a_dir"
        blocker.write_text("x")
        monkeypatch.setattr(_data, "path", [str(blocker / "sub")])
        with pytest.raises(PermissionError):
            _data.make_staging_dir(prefix="nltk_probe_")
