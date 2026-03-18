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
