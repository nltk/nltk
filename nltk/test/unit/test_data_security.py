import gzip
import os
import zipfile

import pytest

import nltk.data as data
from nltk import pathsec


def test_normalize_rejects_no_protocol_traversal():
    """No-protocol traversal sequences should be rejected."""
    with pytest.raises(ValueError):
        data.normalize_resource_url("../../etc/passwd")

    with pytest.raises(ValueError):
        data.normalize_resource_url("../relative/../etc/passwd")


def test_normalize_rejects_no_protocol_backslashes():
    """Windows-style backslash traversal should be rejected when no protocol is present."""
    with pytest.raises(ValueError):
        data.normalize_resource_url(r"..\..\etc\passwd")


def test_normalize_allows_package_paths():
    """Valid package-style resource names should still be treated as nltk: URLs."""
    out = data.normalize_resource_url("corpora/brown")
    assert out.startswith(
        "nltk:"
    ), "Package-style paths should be treated as 'nltk:' URLs"


def test_find_rejects_traversal_direct_call():
    """Defense-in-depth: direct calls to find() should reject traversal-like names."""
    with pytest.raises(ValueError):
        data.find("../../etc/passwd")


def test_find_rejects_traversal_that_becomes_unsafe_after_normalization():
    """
    Defense-in-depth edge case: a path can become unsafe only after normalization.

    Example from review: "foo/../../etc/passwd" normalizes to "../etc/passwd" and
    must still be rejected.
    """
    with pytest.raises(ValueError):
        data.find("foo/../../etc/passwd")


def test_normalize_rejects_no_protocol_absolute_posix_path():
    """Absolute POSIX paths without a protocol should be rejected."""
    with pytest.raises(ValueError):
        data.normalize_resource_url("/etc/passwd")


def test_normalize_rejects_no_protocol_windows_drive_letter_paths():
    """
    Windows drive letter paths should be rejected even on non-Windows platforms.

    Review note: don't gate 'C:/etc/passwd' on Windows only; ensure robust rejection
    regardless of runtime platform.
    """
    with pytest.raises(ValueError):
        data.normalize_resource_url(r"C:\etc\passwd")

    # Run on all platforms (per review suggestion)
    with pytest.raises(ValueError):
        data.normalize_resource_url("C:/etc/passwd")


def test_normalize_rejects_no_protocol_dotdot_only():
    """A resource name that is exactly '..' should be rejected."""
    with pytest.raises(ValueError):
        data.normalize_resource_url("..")


@pytest.mark.parametrize(
    "url",
    [
        # encoded absolute path
        "nltk:%2fetc%2fpasswd",
        "nltk:%2Fetc%2Fpasswd",
        # encoded ".." traversal
        "nltk:corpora/%2e%2e/%2e%2e/etc/passwd",
        "nltk:corpora/%2E%2E/%2E%2E/etc/passwd",
        # encoded separators sandwiching literal ".."
        "nltk:corpora/..%2f..%2fetc%2fpasswd",
        # encoded /proc target
        "nltk:%2fproc%2fself%2fenviron",
        # encoded Windows drive letter
        "nltk:%43%3a%5cetc",
        # encoded backslash traversal
        "nltk:%5c..%5cetc%5cpasswd",
    ],
)
def test_normalize_rejects_url_encoded_traversal(url):
    """URL-encoded path separators and traversal must not bypass the safety check.

    Regression: prior to the fix, ``nltk.data.load("nltk:%2fetc%2fpasswd")``
    decoded the path inside ``url2pathname()`` *after* the safety check ran,
    allowing arbitrary file read. See huntr report
    https://huntr.com/bounties/fae662d6-74c2-44fa-95f3-f53d4e8a8355.
    """
    with pytest.raises(ValueError):
        data.normalize_resource_url(url)


@pytest.mark.parametrize(
    "name",
    [
        "%2fetc%2fpasswd",
        "corpora/%2e%2e/%2e%2e/etc/passwd",
        "corpora/..%2f..%2fetc%2fpasswd",
    ],
)
def test_find_rejects_url_encoded_traversal(name):
    """Defense-in-depth: find() must reject URL-encoded traversal directly."""
    with pytest.raises(ValueError):
        data.find(name)


@pytest.mark.parametrize(
    "url",
    [
        # Encoded space — extremely common in real resource names.
        "nltk:corpora/foo%20bar",
        # UTF-8-encoded non-ASCII name (here "中文").
        "nltk:corpora/%E4%B8%AD%E6%96%87",
        # Encoded ASCII dot in an extension — decodes to ``file.zip``, no traversal.
        "nltk:corpora/file%2Ezip",
        # Mixed safe encoding inside a realistic zipfile-style name.
        "nltk:tokenizers/punkt%2Ezip/punkt/PY3/english.pickle",
    ],
)
def test_normalize_allows_safe_percent_encoded_names(url):
    """Percent-encoded characters that decode to *safe* path components
    must not be falsely rejected.

    Guards against the centralised encoded-bypass check accidentally
    being tightened into a blanket "any percent-encoding is unsafe" rule.
    """
    out = data.normalize_resource_url(url)
    assert out.startswith("nltk:"), (
        f"Safe encoded name {url!r} should still normalise to an nltk: URL, "
        f"got {out!r}"
    )


@pytest.mark.parametrize(
    "url",
    [
        # Double-encoded "/" — single unquote yields literal "%2f", which is
        # neither a path separator nor a traversal segment.
        "nltk:%252fetc%252fpasswd",
        # Double-encoded ".." — single unquote yields literal "%2e%2e".
        "nltk:corpora/%252e%252e/etc/passwd",
    ],
)
def test_double_encoded_payloads_are_not_exploitable(url):
    """Double-encoded payloads must not reach the host filesystem.

    ``url2pathname()`` only performs one decoding pass, so a double-encoded
    payload resolves to a literal ``%2f...`` resource name *inside* the
    nltk_data search path rather than to ``/etc/passwd`` on the host. We
    intentionally do not chase the asymmetric depth of decoding here — we
    just assert the call fails closed (LookupError for a non-existent
    nltk resource, or ValueError if a future tightening rejects it) and
    never silently returns host-file contents.
    """
    with pytest.raises((LookupError, ValueError)):
        data.load(url, format="raw")


@pytest.mark.parametrize(
    "url",
    [
        "nltk:%2fetc%2fpasswd",
        "nltk:corpora/..%2f..%2fetc%2fpasswd",
        "nltk:corpora/%2e%2e/%2e%2e/etc/passwd",
    ],
)
def test_load_rejects_encoded_traversal_end_to_end(url):
    """End-to-end: the public ``data.load`` entry point must reject the
    same encoded-traversal payloads, not just the internal
    ``normalize_resource_url`` / ``find`` helpers.
    """
    with pytest.raises(ValueError):
        data.load(url, format="raw")


def test_find_zip_split_is_non_greedy(tmp_path):
    # Create a.zip containing an entry whose name includes another ".zip".
    zpath = tmp_path / "a.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("b.zip/c.txt", "ok")

    ptr = data.find("a.zip/b.zip/c.txt", paths=[str(tmp_path)])
    with ptr.open() as f:
        got = f.read()
        if isinstance(got, bytes):
            got = got.decode("utf-8")
        assert got == "ok"


def test_gzip_pointer_open_enforces_sandbox(tmp_path, monkeypatch):
    """GzipFileSystemPathPointer.open() must honour the pathsec sandbox.

    Regression test for the sandbox bypass where the gzip pointer opened its
    path with GzipFile directly instead of routing through pathsec.open()
    (CWE-22 / CWE-73): it must refuse a path outside the allowed roots and an
    in-root symlink that escapes outside, while still reading in-root files.
    """
    allowed = tmp_path / "data"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: {allowed.resolve()})

    # gzip file OUTSIDE the allowed root -> blocked
    secret = outside / "secret.gz"
    with gzip.open(secret, "wb") as fh:
        fh.write(b"secret")
    with pytest.raises((PermissionError, ValueError)):
        data.GzipFileSystemPathPointer(str(secret)).open().read()

    # in-root symlink escaping outside the allowed root -> blocked
    link = allowed / "link.gz"
    try:
        os.symlink(secret, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported in this environment")
    with pytest.raises((PermissionError, ValueError)):
        data.GzipFileSystemPathPointer(str(link)).open().read()

    # legitimate gzip INSIDE the allowed root -> reads (decompressed)
    good = allowed / "good.gz"
    with gzip.open(good, "wb") as fh:
        fh.write(b"hello-gz")
    with data.GzipFileSystemPathPointer(str(good)).open() as fp:
        assert fp.read() == b"hello-gz"


# ---------------------------------------------------------------------------
# retrieve() write sink must honour the pathsec sandbox (CWE-22; CVE-2026-12871)
# ---------------------------------------------------------------------------

_RETRIEVE_PAYLOAD = b"ARBITRARY-FILE-WRITE-PAYLOAD"


def test_retrieve_write_enforces_pathsec_sandbox(tmp_path, monkeypatch):
    """Under ``ENFORCE``, an out-of-root write target is rejected; in-root works.

    ``retrieve`` used the builtin ``open(..., "wb")`` for the destination, which
    bypassed pathsec and allowed arbitrary local file writes outside the sandbox.
    """
    allowed = tmp_path / "data"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: {allowed.resolve()})

    # An in-root source whose bytes become the copied content.
    src = allowed / "src.txt"
    src.write_bytes(_RETRIEVE_PAYLOAD)
    url = src.resolve().as_uri()  # RFC 8089 file URL (portable across platforms)

    # Out-of-root target: the global sandbox (no required_root) raises
    # PermissionError, and nothing must be written.
    target = outside / "evil.txt"
    with pytest.raises(PermissionError):
        data.retrieve(url, filename=str(target), verbose=False)
    assert not target.exists()

    # In-root target still works and copies the bytes.
    ok = allowed / "copy.txt"
    data.retrieve(url, filename=str(ok), verbose=False)
    assert ok.read_bytes() == _RETRIEVE_PAYLOAD


def test_retrieve_write_unchanged_when_sandbox_disabled(tmp_path, monkeypatch):
    """With the sandbox off, an out-of-root target still writes (only warns)."""
    monkeypatch.setattr(pathsec, "ENFORCE", False)
    # Force *no* allowed roots so the target is unambiguously out-of-root
    # (tmp_path is usually inside tempfile.gettempdir(), which is allowed by
    # default -- that would not exercise the disabled-sandbox path).
    monkeypatch.setattr(pathsec, "_get_allowed_roots", set)
    src = tmp_path / "src.txt"
    src.write_bytes(_RETRIEVE_PAYLOAD)
    target = tmp_path / "out.txt"
    # Not enforcing: pathsec warns about the out-of-root path but still writes.
    with pytest.warns(RuntimeWarning):
        data.retrieve(src.resolve().as_uri(), filename=str(target), verbose=False)
    assert target.read_bytes() == _RETRIEVE_PAYLOAD
