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
``0177.0.0.1`` is NOT loopback. The C resolver reads ``0177`` as decimal 177
(leading zero, not octal), so it resolves to the public 177.0.0.1 and is
correctly allowed. ``0x7f.0.0.1`` really is 127.0.0.1 and is refused. The guard
follows what getaddrinfo will actually do, so these tests assert the resolver's
interpretation, not a guessed one.
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


def test_leading_zero_host_is_decimal_not_octal():
    """0177.0.0.1 resolves to the PUBLIC 177.0.0.1, so refusing it would be an
    over-block. Pinned because it looks like a loopback bypass at a glance."""
    resolved = sorted({info[4][0] for info in socket.getaddrinfo("0177.0.0.1", 80)})
    assert resolved == ["177.0.0.1"], resolved
    assert _verdict("http://0177.0.0.1/") == "allowed"


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
