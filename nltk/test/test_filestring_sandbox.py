import io
import os

import pytest

from nltk.util import filestring


def test_reads_allowed_file(tmp_path):
    """filestring should read files inside allowed_dir"""
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    f = allowed_dir / "example.txt"
    f.write_text("hello world")

    output = filestring(str(f), allowed_dir=str(allowed_dir))
    assert output == "hello world"


def test_rejects_parent_traversal(tmp_path):
    """filestring should block ../ traversal attempts"""
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    secret = tmp_path / "secret.txt"
    secret.write_text("topsecret")

    # simulate ../ traversal
    traversal_path = str(allowed / ".." / "secret.txt")

    with pytest.raises(PermissionError):
        filestring(traversal_path, allowed_dir=str(allowed))


def test_rejects_symlink_escape(tmp_path):
    """filestring should block symlink pointing outside allowed_dir"""
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("hidden-data")

    link = allowed / "link.txt"

    # On Windows, symlink creation may require admin — skip cleanly if not allowed
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported on this platform")

    with pytest.raises(PermissionError):
        filestring(str(link), allowed_dir=str(allowed))


def test_preserves_file_like_objects():
    """filestring should maintain legacy behavior for stream-like objects"""
    stream = io.StringIO("stream-data")
    assert filestring(stream) == "stream-data"


def test_encoding_fallback(tmp_path):
    """filestring should tolerate decoding errors when reading files"""
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    f = allowed / "latin1.txt"
    f.write_bytes(b"caf\xe9")  # invalid UTF-8 sequence

    output = filestring(str(f), allowed_dir=str(allowed))
    assert isinstance(output, str)
    assert "caf" in output  # partial decode allowed via errors="ignore"
