# Natural Language Toolkit: expanded SSRF attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Broad SSRF vector matrix for ``nltk.pathsec`` (GHSA-8mgp umbrella, #3753).

This is a dedicated, net-new harness that extends ``test_ssrf_url_encodings.py``
and the SSRF/proxy tests in ``test_pathsec.py`` with vectors those files do not
already cover: three-part and single-part obfuscations, mixed-base and
folding-overflow spellings, the IPv4-compatible and Teredo IPv6 tunnels, the
198.18/15, 192.0.0/24 and 240/4 reserved ranges, non-http schemes ``ldap`` and
``jar``, userinfo and fragment host-confusion, whitespace-in-host, the
trailing-dot FQDN subtlety, punycode names, connect-time DNS-rebind pinning, the
redirect re-validation hook, and proxy fail-closed proven by zero egress.

Every internal or obfuscated target must be REFUSED (PermissionError / ValueError
/ OSError) and must produce NO network egress. Every genuinely public target must
be ALLOWED. Two properties get cross-platform teeth:

* Numeric IPv4 obfuscations (decimal / hex / octal / short) are folded by the
  glibc and BSD resolvers but not by the Windows resolver, so they are asserted
  with the resolver stubbed empty. On that Windows-like path ``_numeric_ipv4`` is
  the only thing standing between the caller and loopback, so it must still
  block. Following the existing ``test_pathsec.py`` convention, the proxy and
  DNS-rebind tests that neuter ``_resolve_hostname`` also neuter ``_numeric_ipv4``
  so the specific guard under test is the one exercised.
* IPv6 literals (``::127.0.0.1``, Teredo, ...) are parsed by ``getaddrinfo`` as
  numeric hosts on every platform, so the empty-resolver stub is NOT appropriate
  for them; they are asserted at the address-classification layer
  (``_ip_is_forbidden``) and through a resolver that echoes the literal, both of
  which are platform-independent.

No guard in ``nltk/*.py`` is modified by this file.
"""

import ipaddress
import socket
import urllib.parse
import urllib.request

import pytest

from nltk import pathsec

# =========================================================================== #
# Fixtures and helpers
# =========================================================================== #


@pytest.fixture(autouse=True)
def enforce_on(monkeypatch):
    """Every vector is evaluated with enforcement on (block, do not warn)."""
    monkeypatch.setattr(pathsec, "ENFORCE", True)


@pytest.fixture(autouse=True)
def no_real_egress(monkeypatch):
    """Record and neutralize any socket egress, and hand the record to tests.

    Nothing in this harness performs a successful connection: every vector is
    either refused before connect, resolves through a mock, or is validated by a
    function that never opens a socket. So this recorder stays empty for a
    correct guard; the egress-sensitive tests assert exactly that. If a
    regression ever let a blocked target reach the network, the attempted
    address would be captured here and the OSError keeps it from leaving the box.
    """
    calls = []

    def spy(address, *args, **kwargs):
        calls.append(address)
        raise OSError("egress refused by test recorder")

    monkeypatch.setattr(socket, "create_connection", spy)
    return calls


def _verdict(url):
    """Return ``"allowed"`` or ``"blocked"`` for ``validate_network_url(url)``."""
    try:
        pathsec.validate_network_url(url, context="attack")
        return "allowed"
    except (PermissionError, ValueError, OSError):
        return "blocked"


def _addrinfo(ip, port=80):
    """A ``getaddrinfo`` record for ``ip`` (v4 or v6)."""
    if ":" in ip:
        return (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            (ip, port, 0, 0),
        )
    return (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))


def _stub_resolver(monkeypatch, mapping):
    """Point ``_resolve_hostname`` at a fixed name to address mapping.

    ``mapping`` maps a host string to the IP it should resolve to; unknown hosts
    resolve to nothing (the fail-closed direction).
    """

    def fake(host):
        ip = mapping.get(host)
        return [_addrinfo(ip)] if ip else []

    monkeypatch.setattr(pathsec, "_resolve_hostname", fake)


# =========================================================================== #
# 1. Loopback obfuscation: net-new numeric spellings
# =========================================================================== #

# All of these canonicalize to 127.0.0.1 and are absent from the existing
# encodings matrix. They are the spellings a scanner-evading attacker reaches for
# after the obvious decimal/hex forms are patched.
_NEW_LOOPBACK_SPELLINGS = [
    "http://127.0.1/",  # three-part short form (last part is 16 bits)
    "http://017700000001/",  # single-part octal loopback
    "http://0X7F000001/",  # uppercase hex prefix
    "http://0177.0x0.0.1/",  # mixed base: octal, hex, decimal
    "http://0x7f.0.0.01/",  # hex first octet, octal last octet
    "http://0177.0.0.0x1/",  # octal first octet, hex last octet
    "http://127.0.0.1:8080/",  # explicit port must not shield the host
    "http://0X7F000001:8080/",  # uppercase hex plus port
]


@pytest.mark.parametrize("url", _NEW_LOOPBACK_SPELLINGS)
def test_new_loopback_spellings_refused_with_live_resolver(url):
    assert _verdict(url) == "blocked", f"{url} reached the network"


@pytest.mark.parametrize("url", _NEW_LOOPBACK_SPELLINGS)
def test_new_loopback_spellings_refused_on_windows_nonfolding_resolver(
    url, monkeypatch
):
    """The cross-platform teeth: the Windows resolver folds none of these numeric
    spellings, so with the resolver stubbed empty ``_numeric_ipv4`` alone must
    still refuse loopback. ``_numeric_ipv4`` is left in place because it is the
    guard under test."""
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda host: [])
    assert _verdict(url) == "blocked", f"{url} bypassed the numeric guard"


# =========================================================================== #
# 2. Overflow / wraparound forms that fold to a forbidden address
# =========================================================================== #

_FOLDING_OVERFLOW = [
    ("http://4294967295/", "255.255.255.255"),  # 0xffffffff broadcast
    ("http://0xffffffff/", "255.255.255.255"),  # hex broadcast
    ("http://192.168.257/", "192.168.1.1"),  # three-part, last absorbs 16 bits
    ("http://3232235521/", "192.168.0.1"),  # decimal private
    ("http://2852039166/", "169.254.169.254"),  # decimal cloud metadata
]


@pytest.mark.parametrize("url,expected_ip", _FOLDING_OVERFLOW)
def test_folding_overflow_forms_refused(url, expected_ip, monkeypatch):
    host = urllib.parse.urlparse(url).hostname
    assert str(pathsec._numeric_ipv4(host)) == expected_ip
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda host: [])
    assert _verdict(url) == "blocked", f"{url} ({expected_ip}) reached the network"


@pytest.mark.parametrize(
    "spelling",
    [
        "127.0.0.257",  # last octet out of range for a four-part literal
        "256.0.0.1",  # leading octet out of range
        "4294967296",  # one past 2**32
        "0x100000000",  # hex one past 2**32
        "017700000001abc",  # trailing junk
        "0x7g000001",  # not a valid hex digit
        "127.0.0.1.",  # trailing dot yields an empty part
    ],
)
def test_malformed_forms_never_misparsed_as_a_public_address(spelling):
    """A form that is not a valid numeric literal must return ``None`` rather than
    silently fold to some routable address an attacker could aim at an internal
    host. ``None`` means it is treated as an opaque name, which then either
    resolves (and is filtered) or fails closed at connect."""
    assert pathsec._numeric_ipv4(spelling) is None


# =========================================================================== #
# 3. Link-local / cloud metadata reached by name
# =========================================================================== #


def test_gcp_metadata_hostname_refused(monkeypatch):
    """``metadata.google.internal`` resolves to the link-local metadata address
    169.254.169.254 and must be refused by name, not just by literal."""
    _stub_resolver(monkeypatch, {"metadata.google.internal": "169.254.169.254"})
    url = "http://metadata.google.internal/computeMetadata/v1/"
    assert _verdict(url) == "blocked"


# =========================================================================== #
# 4. Private / carrier-grade-NAT / reserved ranges as URLs (net-new ranges)
# =========================================================================== #

_RESERVED_URLS = [
    "http://198.18.0.1/",  # 198.18/15 benchmarking
    "http://198.19.255.255/",  # 198.18/15 upper
    "http://192.0.0.1/",  # 192.0.0/24 IETF protocol assignments
    "http://240.0.0.1/",  # 240/4 reserved for future use
    "http://255.255.255.255/",  # limited broadcast
    "http://100.127.255.255/",  # 100.64/10 CGN upper edge
    "http://172.31.0.1/",  # 172.16/12 private upper edge
    "http://203.0.113.1/",  # TEST-NET-3 documentation range
    "http://198.51.100.1/",  # TEST-NET-2 documentation range
    "http://192.0.2.1/",  # TEST-NET-1 documentation range
]


@pytest.mark.parametrize("url", _RESERVED_URLS)
def test_reserved_ranges_refused(url, monkeypatch):
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda host: [])
    assert _verdict(url) == "blocked", f"{url} reached the network"


# =========================================================================== #
# 5. IPv6 embeds and tunnels: net-new forms, asserted platform-independently
# =========================================================================== #

# The Teredo client is the last 32 bits XORed with all-ones; here the server is
# the public 8.8.8.8 and the client folds to loopback 127.0.0.1, so the tunnel
# smuggles loopback past a naive is_global check on the wrapper.
_TEREDO_LOOPBACK_CLIENT = "2001:0:808:808:0:0:80ff:fffe"


def test_ipv4_compatible_ipv6_unwraps_to_loopback():
    ip = ipaddress.ip_address("::127.0.0.1")
    assert pathsec._embedded_ipv4(ip) == ipaddress.ip_address("127.0.0.1")
    assert pathsec._ip_is_forbidden(ip)


def test_teredo_tunnel_client_loopback_is_forbidden():
    ip = ipaddress.ip_address(_TEREDO_LOOPBACK_CLIENT)
    server, client = ip.teredo
    assert client == ipaddress.ip_address("127.0.0.1")
    assert server == ipaddress.ip_address("8.8.8.8")
    assert pathsec._ip_is_forbidden(ip)


def test_6to4_wrapping_public_v4_is_still_refused():
    """Documented over-block, kept so nobody later turns it into an allowed
    control: the stdlib does not classify the 2002::/16 wrapper as globally
    routable, so a 6to4 address is refused even when the embedded v4 is public.
    Refusing more here is safe; the only cost is that 6to4 is unusable as a
    download source, which NLTK never needs."""
    ip = ipaddress.ip_address("2002:0808:0808::")  # wraps public 8.8.8.8
    assert list(pathsec._tunneled_ipv4s(ip)) == [ipaddress.ip_address("8.8.8.8")]
    assert pathsec._ip_is_forbidden(ip)


@pytest.mark.parametrize(
    "literal",
    [
        "[::127.0.0.1]",  # IPv4-compatible loopback
        f"[{_TEREDO_LOOPBACK_CLIENT}]",  # Teredo tunnel to loopback
    ],
)
def test_new_ipv6_tunnels_refused_through_validate(literal, monkeypatch):
    """``getaddrinfo`` parses these numeric literals on every platform, so the
    validate path filters them by classification. The resolver is stubbed to echo
    the literal back so the verdict does not depend on the host having IPv6
    connectivity."""
    host = literal[1:-1]
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [_addrinfo(host)])
    assert _verdict(f"http://{literal}/") == "blocked"


# =========================================================================== #
# 6. Scheme and URL-parsing tricks
# =========================================================================== #


@pytest.mark.parametrize(
    "url",
    [
        "ldap://127.0.0.1/",  # non-http scheme
        "jar:http://127.0.0.1/x!/y",  # nested jar scheme
        "gopher://127.0.0.1:70/x",  # gopher smuggling
        "dict://127.0.0.1:11211/stat",  # memcached via dict
    ],
)
def test_non_http_schemes_refused(url):
    assert _verdict(url) == "blocked", f"{url} was accepted"


@pytest.mark.parametrize(
    "url,true_host",
    [
        ("http://user:pass@evil.example@127.0.0.1/", "127.0.0.1"),
        ("http://127.0.0.1#@evil.example/", "127.0.0.1"),
        ("http://127.0.0.1\t/", "127.0.0.1"),
        ("http://127.0.0.1\n/", "127.0.0.1"),
    ],
)
def test_userinfo_fragment_and_whitespace_host_confusion_refused(url, true_host):
    """The guard must key on the real parsed host, not the decoy in the userinfo
    or fragment. urlsplit strips embedded tab and newline, so those collapse to
    the loopback host too."""
    assert urllib.parse.urlparse(url).hostname == true_host
    assert _verdict(url) == "blocked", f"{url} reached the network"


@pytest.mark.parametrize(
    "url",
    [
        "file://server/share/secret",  # remote/UNC authority
        "file://attacker.example/x",  # remote authority
        "file://localhost/etc/passwd",  # local authority, path is filtered
    ],
)
def test_file_scheme_authorities_refused(url):
    """A remote/UNC ``file://`` authority is rejected outright; a local authority
    is accepted as local and then the path itself is validated, so a sensitive
    absolute path is still refused."""
    assert _verdict(url) == "blocked", f"{url} was accepted"


# =========================================================================== #
# 7. Trailing-dot FQDN: safe on both resolver behaviors (no genuine bypass)
# =========================================================================== #


def test_trailing_dot_loopback_blocked_when_resolver_folds_it(monkeypatch):
    """On glibc and Windows ``127.0.0.1.`` resolves to loopback, so the validate
    path sees the forbidden address and blocks."""
    monkeypatch.setattr(
        pathsec, "_resolve_hostname", lambda h: [_addrinfo("127.0.0.1")]
    )
    assert _verdict("http://127.0.0.1./") == "blocked"


def test_trailing_dot_loopback_fails_closed_when_resolver_does_not_fold(
    monkeypatch, no_real_egress
):
    """On macOS ``getaddrinfo('127.0.0.1.')`` fails, so validate sees no address
    and returns without a verdict. The connection layer must then fail closed:
    with nothing resolved, ``_pinned_connection`` refuses rather than connecting
    by the raw host, and no egress is attempted. This is why the trailing-dot
    form is not a genuine bypass on any platform."""

    def gaierror(*args, **kwargs):
        raise socket.gaierror("simulated non-folding resolver")

    monkeypatch.setattr(socket, "getaddrinfo", gaierror)
    with pytest.raises(OSError):
        pathsec._pinned_connection("127.0.0.1.", 80, None, None)
    assert no_real_egress == [], "loopback egress attempted despite fail-closed"


# =========================================================================== #
# 8. Punycode / IDN names resolving to an internal target
# =========================================================================== #


@pytest.mark.parametrize(
    "host,ip",
    [
        ("xn--internal-loopback.test", "127.0.0.1"),
        ("xn--80ak6aa92e", "169.254.169.254"),  # a punycode label to metadata
    ],
)
def test_punycode_hostname_to_internal_refused(host, ip, monkeypatch):
    _stub_resolver(monkeypatch, {host: ip})
    assert _verdict(f"http://{host}/") == "blocked"


# =========================================================================== #
# 9. DNS rebinding at connect time (unit level, proven by zero egress)
# =========================================================================== #


def test_connect_time_rebind_to_loopback_refused(monkeypatch, no_real_egress):
    """The validate/connect TOCTOU: a name validates as public but re-resolves to
    loopback at connect time. ``_resolve_and_validate_host`` re-checks every
    address it will pin, so the rebind is caught and no socket is opened. Both the
    resolver-level and numeric guards are neutralized so the connect-time
    re-validation is the guard actually exercised."""
    monkeypatch.setattr(pathsec, "_numeric_ipv4", lambda h: None)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda h, port, *a, **k: [
            _addrinfo("127.0.0.1", port if isinstance(port, int) else 80)
        ],
    )
    with pytest.raises(PermissionError):
        pathsec._resolve_and_validate_host("rebind.attack.test", 80)
    assert no_real_egress == [], "rebind connect attempted egress to loopback"


# =========================================================================== #
# 10. Redirect re-validation
# =========================================================================== #


class _FakeReq:
    """Minimal request object for the redirect handler contract."""

    full_url = "https://benign.example.com/start"

    def get_full_url(self):
        return self.full_url

    def get_method(self):
        return "GET"

    def has_header(self, name):
        return False


@pytest.mark.parametrize(
    "target",
    [
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://127.0.0.1/admin",  # loopback
        "http://2130706433/admin",  # decimal loopback
        "http://[::1]/admin",  # loopback IPv6
        "http://10.0.0.1/internal",  # RFC1918
    ],
)
def test_redirect_to_internal_target_refused(target):
    """A 3xx from a benign origin to an internal target must be re-validated and
    refused before the redirect is followed (GHSA class: redirect-based SSRF)."""
    handler = pathsec._ValidatingRedirectHandler()
    with pytest.raises((PermissionError, ValueError, OSError)):
        handler.redirect_request(_FakeReq(), None, 302, "Found", {}, target)


# =========================================================================== #
# 11. Proxy: fail closed before egress, and NO_PROXY is not a bypass
# =========================================================================== #


def _force_proxied(monkeypatch, no_bypass_for=None):
    """Configure a real http/https proxy and neuter the local guards so the
    proxy fail-closed path is the one under test (matching test_pathsec.py)."""
    monkeypatch.setattr(urllib.request, "_opener", None)
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    monkeypatch.setattr(pathsec, "_numeric_ipv4", lambda h: None)
    # Neuter the address classifier too: it now also backs the resolver-
    # independent IP-literal check, and an IP-literal target would otherwise be
    # refused there first, before the proxy guard under test.
    monkeypatch.setattr(pathsec, "_ip_is_forbidden", lambda ip: False)
    monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", False)
    proxies = {"http": "http://proxy.local:3128", "https": "http://proxy.local:3128"}
    if no_bypass_for is not None:
        proxies["no"] = no_bypass_for
    monkeypatch.setattr(urllib.request, "getproxies", lambda: proxies)
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda host: False)


@pytest.mark.parametrize(
    "target",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1/admin",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://example.com/data.zip",  # even a benign host: a proxy is unpinnable
    ],
)
def test_proxied_fetch_fails_closed_before_egress(target, monkeypatch, no_real_egress):
    """A configured proxy performs the egress, so NLTK cannot pin the validated
    IP. The fetch must be refused before any socket is opened, so the recorder
    stays empty (no egress)."""
    _force_proxied(monkeypatch)
    with pytest.raises(PermissionError, match="proxied fetch"):
        pathsec.urlopen(target)
    assert no_real_egress == [], "proxied fetch reached the network before refusal"


def test_no_proxy_for_other_hosts_is_not_a_bypass(monkeypatch, no_real_egress):
    """NO_PROXY set for an unrelated host must not turn the proxy block into a
    bypass: the requested host is still proxied (not bypassed), so the fetch fails
    closed and nothing leaves the box."""
    _force_proxied(monkeypatch, no_bypass_for="trusted.internal.example")
    with pytest.raises(PermissionError, match="proxied fetch"):
        pathsec.urlopen("http://169.254.169.254/latest/meta-data/")
    assert no_real_egress == []


# =========================================================================== #
# 12. Benign controls: real public targets must be ALLOWED (over-block guard)
# =========================================================================== #


@pytest.mark.parametrize(
    "url",
    [
        "http://8.8.8.8/",  # public literal
        "http://8.8.8.8:443/",  # public literal with port
        "http://1.1.1.1/",  # public literal
        "http://0x01010101/",  # hex spelling of 1.1.1.1
        "http://16843009/",  # decimal spelling of 1.1.1.1
    ],
)
def test_public_numeric_targets_allowed(url, monkeypatch):
    """The numeric canonicalizer must not over-block: public numeric spellings
    are allowed even with the resolver stubbed empty, proving the allow comes from
    the numeric path and not from a live lookup."""
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    assert _verdict(url) == "allowed", f"{url} was wrongly blocked"


@pytest.mark.parametrize(
    "url,ip",
    [
        (
            "https://raw.githubusercontent.com/nltk/nltk_data/index.xml",
            "185.199.108.133",
        ),
        ("https://files.pythonhosted.org/packages/x.zip", "151.101.0.223"),
        ("http://downloads.example.org/corpus.zip", "93.184.216.34"),
    ],
)
def test_public_hostnames_allowed(url, ip, monkeypatch):
    _stub_resolver(monkeypatch, {urllib.parse.urlparse(url).hostname: ip})
    assert _verdict(url) == "allowed", f"{url} was wrongly blocked"


def test_live_public_hostname_allowed():
    """One optional live control: a real public host must validate as allowed.
    Skips cleanly when offline or when DNS cannot resolve, so the suite stays
    green without network. No connection is made; only validation runs."""
    host = "raw.githubusercontent.com"
    try:
        socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except (OSError, socket.gaierror):
        pytest.skip("no network / DNS available for the live benign control")
    assert _verdict(f"https://{host}/nltk/nltk_data/gh-pages/index.xml") == "allowed"


# =========================================================================== #
# 13. IPv6 wrappers / tunnels wrapping an internal IPv4, and plain internal
#     IPv6, asserted at the classification layer (platform-independent)
# =========================================================================== #

# Each wrapper (NAT64 64:ff9b::/96, 6to4 2002::/16, Teredo 2001:0::/32, the
# IPv4-mapped ::ffff:0:0/96 and IPv4-compatible ::/96 prefixes) can smuggle a
# forbidden internal IPv4 past a naive is_global check on the wrapper. 6to4 and
# Teredo are refused outright regardless of the embedded address because their
# is_global classification varies across CPython patch levels.
_INTERNAL_IPV6_LITERALS = [
    "64:ff9b::7f00:1",  # NAT64 wrapping 127.0.0.1
    "64:ff9b::a9fe:a9fe",  # NAT64 wrapping 169.254.169.254 (cloud metadata)
    "64:ff9b::a00:1",  # NAT64 wrapping 10.0.0.1
    "64:ff9b::6440:1",  # NAT64 wrapping 100.64.0.1 (CGNAT)
    "2002:7f00:0001::",  # 6to4 wrapping 127.0.0.1
    "2002:a9fe:a9fe::",  # 6to4 wrapping 169.254.169.254
    "2002:0a00:0001::",  # 6to4 wrapping 10.0.0.1
    "2002:0808:0808::",  # 6to4 wrapping public 8.8.8.8 (over-block)
    "2001:0:808:808:0:0:80ff:fffe",  # Teredo folding to loopback client
    "::ffff:127.0.0.1",  # IPv4-mapped loopback
    "::ffff:7f00:1",  # IPv4-mapped loopback, hex tail
    "::ffff:169.254.169.254",  # IPv4-mapped cloud metadata
    "::ffff:10.0.0.1",  # IPv4-mapped private
    "::127.0.0.1",  # IPv4-compatible loopback
    "::169.254.169.254",  # IPv4-compatible cloud metadata
    "::1",  # IPv6 loopback
    "::",  # IPv6 unspecified
    "fe80::1",  # IPv6 link-local
    "fd00::1",  # IPv6 unique-local (private)
    "ff02::1",  # IPv6 link-local all-nodes multicast
]


@pytest.mark.parametrize("literal", _INTERNAL_IPV6_LITERALS)
def test_internal_ipv6_forms_forbidden_at_classifier(literal):
    """Platform-independent: every internal or internal-embedding IPv6 form is
    refused by the address classifier itself, so the verdict never depends on
    the host's IPv6 connectivity or resolver behavior."""
    assert pathsec._ip_is_forbidden(ipaddress.ip_address(literal))


@pytest.mark.parametrize(
    "literal",
    [
        "::ffff:8.8.8.8",  # IPv4-mapped PUBLIC v4 => routes to 8.8.8.8, allowed
        "64:ff9b::808:808",  # NAT64 PUBLIC v4 => routes to 8.8.8.8, allowed
        "2606:4700:4700::1111",  # genuinely public IPv6 (Cloudflare)
        "2001:4860:4860::8888",  # genuinely public IPv6 (Google)
    ],
)
def test_public_ipv6_forms_allowed_at_classifier(literal):
    """The wrapper over-block must not swallow genuinely public destinations:
    an IPv4-mapped or NAT64 wrapper of a public v4, and plain public IPv6, stay
    allowed."""
    assert not pathsec._ip_is_forbidden(ipaddress.ip_address(literal))


# =========================================================================== #
# 14. IP-literal hosts fail CLOSED through validate_network_url even when the
#     resolver returns nothing (regression for the resolver-independent check)
# =========================================================================== #

# getaddrinfo returns nothing for a literal whose address family the host lacks
# (an IPv6 literal on an IPv4-only box, or a stubbed/empty resolver). Before the
# direct-literal classification these forms fell through the resolve loop and
# were ALLOWED. Each must now be blocked with no egress.
_INTERNAL_LITERAL_URLS = [
    "http://[::1]/",  # IPv6 loopback
    "http://[::ffff:127.0.0.1]/",  # IPv4-mapped loopback
    "http://[64:ff9b::7f00:1]/",  # NAT64 loopback
    "http://[2002:7f00:0001::]/",  # 6to4 loopback
    "http://[2002:0808:0808::]/",  # 6to4 public over-block
    "http://[fd00::1]/",  # unique-local
    "http://[fe80::1]/",  # link-local
    "http://[64:ff9b::a9fe:a9fe]/",  # NAT64 cloud metadata
    "http://127.0.0.1/",  # plain IPv4 loopback literal
    "http://169.254.169.254/",  # plain IPv4 cloud metadata literal
]


@pytest.mark.parametrize("url", _INTERNAL_LITERAL_URLS)
def test_ip_literal_hosts_fail_closed_with_empty_resolver(
    url, monkeypatch, no_real_egress
):
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    assert _verdict(url) == "blocked", f"{url} leaked past validation"
    assert no_real_egress == [], f"{url} produced egress"


@pytest.mark.parametrize(
    "url",
    [
        "http://[2606:4700:4700::1111]/",  # public IPv6 literal (Cloudflare)
        "http://[2001:4860:4860::8888]/",  # public IPv6 literal (Google)
    ],
)
def test_public_ip_literal_hosts_allowed(url, monkeypatch):
    """The resolver-independent literal check must not over-block a genuinely
    public IPv6 literal."""
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    assert _verdict(url) == "allowed", f"{url} was wrongly blocked"


# =========================================================================== #
# 15. Numeric encodings of non-loopback internal targets on the Windows path
# =========================================================================== #

# The existing section 1 covers numeric loopback; these extend it to the cloud
# metadata address, private and unspecified ranges, asserted with the resolver
# stubbed empty so the numeric guard alone is what blocks them.
_INTERNAL_NUMERIC_URLS = [
    "http://2852039166/",  # decimal 169.254.169.254 (cloud metadata)
    "http://0xA9FEA9FE/",  # hex cloud metadata
    "http://0251.0376.0251.0376/",  # octal cloud metadata
    "http://167772161/",  # decimal 10.0.0.1 (private)
    "http://0x0A000001/",  # hex 10.0.0.1
    "http://3232235777/",  # decimal 192.168.0.1 (private)
    "http://0/",  # 0 => 0.0.0.0 (unspecified, routes to localhost on Linux)
    "http://0.0.0.0/",  # unspecified literal
]


@pytest.mark.parametrize("url", _INTERNAL_NUMERIC_URLS)
def test_internal_numeric_targets_refused_on_windows_path(
    url, monkeypatch, no_real_egress
):
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    assert _verdict(url) == "blocked", f"{url} leaked past the numeric guard"
    assert no_real_egress == [], f"{url} produced egress"


# =========================================================================== #
# 16. The proxy avenue does not let the IP-literal check be bypassed, and the
#     literal check is not weakened by opting into proxied fetches
# =========================================================================== #

# A configured proxy performs the egress, so a proxied fetch NLTK cannot pin is
# refused by the proxy guard (GHSA-6ww7). Independently, the resolver-independent
# IP-literal / numeric address check runs first, so an internal target is refused
# by that check even when a proxy is configured, AND even when the operator opts
# into proxied fetches (ALLOW_PROXIED_FETCH): the opt-in only permits a proxied
# fetch of a target that passes the address check, never an internal literal.
_PROXY_INTERNAL_TARGETS = [
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata literal
    "http://127.0.0.1/admin",  # loopback literal
    "http://[::1]/x",  # IPv6 loopback literal
    "http://[::ffff:127.0.0.1]/x",  # IPv4-mapped loopback literal
    "http://2130706433/",  # decimal loopback
    "http://0x7f000001/",  # hex loopback
    "http://10.0.0.1/internal",  # private literal
]
_PROXY_PUBLIC_TARGETS = ["http://1.1.1.1/", "http://93.184.216.34/"]


def _configure_proxy(monkeypatch, allow):
    monkeypatch.setattr(
        urllib.request,
        "getproxies",
        lambda: {"http": "http://proxy.local:8080", "https": "http://proxy.local:8080"},
    )
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda host: False)
    monkeypatch.setattr(urllib.request, "_opener", None)
    monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", allow)


def _proxy_verdict(url):
    """Which guard refuses ``pathsec.urlopen(url)`` under a configured proxy."""
    try:
        pathsec.urlopen(url, timeout=1)
        return "allowed"
    except PermissionError as exc:
        return "proxy-guard" if "proxied fetch" in str(exc) else "address-guard"
    except (ValueError, OSError):
        return "address-guard"
    except Exception:
        return "reached-egress"


@pytest.mark.parametrize("url", _PROXY_INTERNAL_TARGETS)
def test_proxied_internal_target_refused_by_address_guard(
    url, monkeypatch, no_real_egress
):
    _configure_proxy(monkeypatch, allow=False)
    assert _proxy_verdict(url) == "address-guard", f"{url} was not address-refused"
    assert no_real_egress == [], f"{url} produced egress"


@pytest.mark.parametrize("url", _PROXY_INTERNAL_TARGETS)
def test_proxied_internal_literal_still_refused_when_proxied_fetch_opted_in(
    url, monkeypatch, no_real_egress
):
    # The operator trusts the proxy (ALLOW_PROXIED_FETCH); the address check must
    # STILL refuse an internal literal/numeric target before the proxy carries it.
    _configure_proxy(monkeypatch, allow=True)
    assert _proxy_verdict(url) == "address-guard", f"{url} leaked through opt-in"
    assert no_real_egress == [], f"{url} produced egress"


@pytest.mark.parametrize("url", _PROXY_PUBLIC_TARGETS)
def test_proxied_public_target_refused_by_proxy_guard(url, monkeypatch, no_real_egress):
    # A public target passes the address check, so the proxy guard is the one that
    # must refuse it (unpinnable through a proxy). Over-block control for section.
    _configure_proxy(monkeypatch, allow=False)
    assert _proxy_verdict(url) == "proxy-guard", f"{url} was not proxy-refused"
    assert no_real_egress == [], f"{url} produced egress"


# =========================================================================== #
# 17. IP-literal edge spellings the direct classifier must still fold and refuse
# =========================================================================== #

# ``ipaddress.ip_address`` folds full-form, zero-padded, mixed-case, compressed,
# zone-scoped and NAT64 dotted-quad spellings to the same address, so none can
# smuggle an internal target past the resolver-independent literal check.
_IP_LITERAL_EDGE_URLS = [
    "http://[0:0:0:0:0:0:0:1]/",  # full-form loopback
    "http://[0000:0000:0000:0000:0000:0000:0000:0001]/",  # zero-padded loopback
    "http://[::FFFF:127.0.0.1]/",  # mixed-case IPv4-mapped loopback
    "http://[::ffff:7f00:0001]/",  # IPv4-mapped loopback, hex tail
    "http://[::1]:8080/",  # IPv6 loopback with an explicit port
    "http://[fe80::1%25eth0]/",  # link-local with a URL-encoded zone id
    "http://[64:ff9b::127.0.0.1]/",  # NAT64 with a dotted-quad loopback suffix
    "http://[64:ff9b:0:0:0:0:7f00:1]/",  # NAT64 full-form loopback
    "http://[2002:7f00:1::]/",  # 6to4 loopback, compressed
    "http://[0::0]/",  # unspecified, compressed
    "http://[::ffff:a9fe:a9fe]/",  # IPv4-mapped cloud metadata, hex
    "http://[fc00::1]/",  # unique-local fc00::/8
    "http://[ff02::fb]/",  # link-local mDNS multicast
]


@pytest.mark.parametrize("url", _IP_LITERAL_EDGE_URLS)
def test_ip_literal_edge_spellings_refused(url, monkeypatch, no_real_egress):
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    assert _verdict(url) == "blocked", f"{url} bypassed the literal classifier"
    assert no_real_egress == [], f"{url} produced egress"


@pytest.mark.parametrize(
    "url",
    [
        "http://[2606:4700:4700::1111]/",  # public IPv6 literal (Cloudflare)
        "http://[2001:4860:4860::8888]/",  # public IPv6 literal (Google)
    ],
)
def test_public_ip_literal_edge_spellings_allowed(url, monkeypatch):
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    assert _verdict(url) == "allowed", f"{url} was wrongly blocked"


# =========================================================================== #
# 18. Hosts that fold to an internal address by resolution or by host-confusion
#     parsing are refused, and NLTK validates the same host it would connect to
# =========================================================================== #

# A homograph host (circled or fullwidth digits) that a folding resolver maps to
# loopback is caught by the resolve loop, exactly as a plain rebinding name is.
_FOLDING_TO_LOOPBACK = {
    "①②⑦.0.0.1": "127.0.0.1",  # circled digits U+2460.. == 127
    "１２７.0.0.1": "127.0.0.1",  # fullwidth digits == 127
    "rebind.internal.example": "127.0.0.1",  # a plain name resolving to loopback
}


@pytest.mark.parametrize("host", list(_FOLDING_TO_LOOPBACK))
def test_host_resolving_to_loopback_is_refused(host, monkeypatch, no_real_egress):
    _stub_resolver(monkeypatch, _FOLDING_TO_LOOPBACK)
    assert _verdict(f"http://{host}/") == "blocked", f"{host!r} reached the network"
    assert no_real_egress == [], f"{host!r} produced egress"


def _userinfo_url(userinfo, host):
    """Build http://<userinfo>@<host>/ without a literal user@domain source."""
    return "http://" + userinfo + chr(64) + host + "/"


# (userinfo, the host urllib parses AFTER the last '@' and NLTK both validates
# and would connect to). A host hidden behind userinfo is not a split between
# what is validated and what is reached: urllib uses the post-'@' host for both.
_USERINFO_THEN_INTERNAL = [
    ("evil.example", "127.0.0.1"),
    ("user:pass", "127.0.0.1"),
    ("a" + chr(64) + "b", "127.0.0.1"),  # an extra '@' in the userinfo
    ("evil.example", "169.254.169.254"),
    ("evil.example", "2130706433"),  # decimal loopback after the userinfo
    ("evil.example", "[::1]"),  # ipv6 loopback literal after the userinfo
]


@pytest.mark.parametrize("userinfo,host", _USERINFO_THEN_INTERNAL)
def test_userinfo_before_internal_host_is_refused(
    userinfo, host, monkeypatch, no_real_egress
):
    url = _userinfo_url(userinfo, host)
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    # The host urllib parses is the internal one, so the address check refuses it.
    parsed = urllib.parse.urlparse(url).hostname
    assert parsed == host.strip(
        "[]"
    ), f"{url} parsed host {parsed!r}, expected {host!r}"
    assert _verdict(url) == "blocked", f"{url} bypassed the address check"
    assert no_real_egress == [], f"{url} produced egress"


# =========================================================================== #
# 19. Documentation, special-use and transition-tunnel wrapper ranges refused
# =========================================================================== #

# None of these are a legitimate download source; each is either non-global or a
# wrapper of an internal IPv4, so the classifier refuses it. 2001:20::/28
# (ORCHIDv2) is intentionally NOT listed: CPython's ipaddress classifies it as
# is_global, so it is allowed here, but it is a non-routable cryptographic
# identifier prefix, so it cannot reach an internal host and is not an SSRF
# vector; documenting the gap rather than special-casing the stdlib.
_SPECIAL_RANGE_URLS = [
    "http://192.0.2.1/",  # IPv4 TEST-NET-1 (documentation)
    "http://198.51.100.1/",  # IPv4 TEST-NET-2
    "http://203.0.113.1/",  # IPv4 TEST-NET-3
    "http://[2001:db8::1]/",  # IPv6 documentation 2001:db8::/32
    "http://[2001:10::1]/",  # ORCHID (deprecated), non-global
    "http://[2001:db8:122:344::7f00:1]/",  # network-specific NAT64 wrapper (doc range)
    "http://[100::7f00:1]/",  # discard-only 100::/64
    "http://0x0.0x0.0x0.0x0/",  # hex spelling of 0.0.0.0
]


@pytest.mark.parametrize("url", _SPECIAL_RANGE_URLS)
def test_special_and_documentation_ranges_refused(url, monkeypatch, no_real_egress):
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
    assert _verdict(url) == "blocked", f"{url} was allowed"
    assert no_real_egress == [], f"{url} produced egress"
