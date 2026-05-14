import zipfile

import pytest

import nltk.data as data


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
