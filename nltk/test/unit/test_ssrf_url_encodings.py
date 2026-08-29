# Natural Language Toolkit: SSRF encoding matrix for the downloader
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``validate_network_url`` must refuse every spelling of an internal target.

Attackers disguise loopback, link-local and private addresses as decimal, hex,
octal, IPv4-mapped IPv6, and NAT64/6to4 tunnels. The cloud-metadata address
(169.254.169.254) is the highest-value SSRF target.

A subtlety the tests encode rather than gloss over: a spelling like
``0177.0.0.1`` is interpreted differently per platform. The BSD/macOS resolver
reads ``0177`` as decimal 177, resolving to the public 177.0.0.1; glibc on Linux
reads it as octal, resolving to loopback 127.0.0.1. ``0x7f.0.0.1`` really is
127.0.0.1 everywhere and is refused. The guard follows whatever getaddrinfo
actually returns, so the test below pins its verdict to the live resolution
rather than to a single platform's guess.
"""

import socket

import pytest

from nltk import pathsec


def _verdict(url):
    try:
        pathsec.validate_network_url(url, context="test")
        return "allowed"
    except (PermissionError, ValueError, OSError):
        return "blocked"


@pytest.fixture(autouse=True)
def enforce_on(monkeypatch):
    monkeypatch.setattr(pathsec, "ENFORCE", True)


_INTERNAL = [
    "http://127.0.0.1/",
    "http://2130706433/",
    "http://0x7f000001/",
    "http://0x7f.0.0.1/",
    "http://127.1/",
    "http://0/",
    "http://0.0.0.0/",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://[::ffff:7f00:1]/",
    "http://[64:ff9b::7f00:1]/",
    "http://[2002:7f00:1::]/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[fd00:ec2::254]/",
    "http://100.64.0.1/",
    "http://10.0.0.1/",
    "http://192.168.1.1/",
    "http://172.16.0.1/",
    "http://[::]/",
    "http://[fe80::1]/",
]


@pytest.mark.parametrize("url", _INTERNAL)
def test_internal_addresses_are_refused(url):
    assert _verdict(url) == "blocked", f"{url} reached the network"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "file://attacker.com/x",
        "gopher://127.0.0.1/",
        "ftp://127.0.0.1/",
        "dict://127.0.0.1:11211/",
        "nltk://x",
    ],
)
def test_non_http_schemes_are_refused(url):
    assert _verdict(url) == "blocked", f"{url} was accepted"


def test_leading_zero_octal_loopback_is_always_refused():
    """0177.0.0.1 is octal-obfuscated loopback (0177 == 127). glibc reads it as
    octal, BSD/macOS as decimal, and the Windows resolver folds neither. The
    guard canonicalizes numeric IPv4 forms itself, so it refuses this on every
    platform rather than deferring to the resolver's inconsistent reading."""
    assert _verdict("http://0177.0.0.1/") == "blocked"


@pytest.mark.parametrize(
    "url",
    [
        "http://2130706433/",
        "http://0x7f000001/",
        "http://0x7f.0.0.1/",
        "http://127.1/",
        "http://0177.0.0.1/",
        "http://0/",
    ],
)
def test_obfuscated_numeric_ip_refused_even_when_resolver_returns_nothing(
    url, monkeypatch
):
    """Regression teeth for the Windows non-folding resolver. glibc and BSD fold
    obfuscated numeric IPv4 spellings to loopback at resolution time, but the
    Windows resolver returns nothing for them, so before the canonicalizer these
    reached the network there. With the resolver stubbed empty (the Windows
    behavior), the guard must still refuse every spelling on its own."""
    monkeypatch.setattr(pathsec, "_resolve_hostname", lambda host: [])
    assert _verdict(url) == "blocked", f"{url} reached the network"


def test_public_numeric_ip_still_allowed(monkeypatch):
    """Over-block control for the canonicalizer: a public numeric spelling
    (0x08080808 == 8.8.8.8) must not be refused by the numeric guard."""
    monkeypatch.setattr(
        pathsec,
        "_resolve_hostname",
        lambda host: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))],
    )
    assert _verdict("http://0x08080808/") == "allowed"


def test_a_hostname_resolving_to_loopback_is_refused(monkeypatch):
    """DNS names are only as safe as what they resolve to. A name pointing at
    127.0.0.1 must be refused as if the literal IP were given."""

    def fake_getaddrinfo(host, *args, **kwargs):
        if host == "evil.internal.test":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
        return socket.getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(pathsec.socket, "getaddrinfo", fake_getaddrinfo)
    assert _verdict("http://evil.internal.test/") == "blocked"


def test_a_public_index_url_is_allowed(monkeypatch):
    """Over-block control: the real download source must not be refused."""

    def fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("185.199.108.133", 443))]

    monkeypatch.setattr(pathsec.socket, "getaddrinfo", fake_getaddrinfo)
    assert _verdict("https://raw.githubusercontent.com/nltk/nltk_data/index.xml") == (
        "allowed"
    )
