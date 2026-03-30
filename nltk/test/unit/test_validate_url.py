"""Unit tests for _validate_url SSRF protection in nltk.downloader."""

import pytest

from nltk.downloader import _validate_url


def test_valid_https():
    _validate_url("https://nltk.org/data.zip")


def test_valid_http():
    _validate_url("http://example.com/file.zip")


def test_github_raw_valid():
    _validate_url("https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/index.xml")


def test_ftp_blocked():
    with pytest.raises(ValueError, match="Only http/https"):
        _validate_url("ftp://evil.com")


def test_file_blocked():
    with pytest.raises(ValueError, match="Only http/https"):
        _validate_url("file:///etc/passwd")


def test_localhost_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://localhost/evil")


def test_127_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://127.0.0.1/evil")


def test_zero_ip_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://0.0.0.0/evil")


def test_link_local_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://169.254.169.254/evil")


def test_private_10_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://10.0.0.1/evil")


def test_private_192_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://192.168.1.1/evil")


def test_gcp_metadata_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://metadata.google.internal")


def test_ipv6_localhost_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://::1/evil")


def test_ipv6_bracketed_blocked():
    with pytest.raises(ValueError):
        _validate_url("http://[::1]/evil")
