import builtins
import io
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
