"""Regression tests for path traversal in NKJPCorpusReader (CWE-22).

The NKJP views build file paths from the caller-supplied ``fileids`` and read
them with the builtin ``open()``, bypassing the ``CorpusReader.open()`` /
``nltk.pathsec`` sandbox.  A ``..`` sequence, an absolute path, or an in-root
symlink in ``fileids`` must not be allowed to escape the corpus root.  The
containment check is symlink-aware (``nltk.pathsec.validate_path`` resolves the
path before comparing), so ``os.path.abspath`` is not enough to fool it.

The paths below are built with ``os.sep`` / ``os.path.join`` / ``os.pardir``
so the tests behave identically on POSIX and Windows.
"""

import os

import pytest

from nltk.corpus.reader.nkjp import NKJPCorpusReader

_HEADER = (
    "<teiHeader><fileDesc><sourceDesc><bibl>"
    "<title>{title}</title>"
    "</bibl></sourceDesc></fileDesc></teiHeader>"
)


def _make_corpus(tmp_path):
    root = tmp_path / "corpus"
    (root / "sample").mkdir(parents=True)
    (root / "sample" / "header.xml").write_text(_HEADER.format(title="IN-ROOT"))
    return root


def _reader(root):
    # The trailing separator is added with os.sep, so the root keeps the shape
    # the reader is normally given without hard-coding a POSIX "/".
    return NKJPCorpusReader(root=str(root) + os.sep, fileids="sample")


def test_nkjp_header_default_fileids_still_works(tmp_path):
    """The legitimate (in-root) flow must keep working after the fix."""
    reader = _reader(_make_corpus(tmp_path))
    out = reader.header()
    assert out and out[0]["title"] == "IN-ROOT"


def test_nkjp_header_rejects_traversal_fileid(tmp_path):
    """A ../ traversal in fileids must be rejected, not read from disk."""
    root = _make_corpus(tmp_path)

    secret_dir = tmp_path / "outside"
    secret_dir.mkdir()
    (secret_dir / "header.xml").write_text(_HEADER.format(title="SECRET"))

    reader = _reader(root)
    # Climb out of the corpus root into the sibling "outside" directory.
    evil = os.path.join(str(root), os.pardir, "outside") + os.sep
    with pytest.raises(ValueError):
        reader.header(fileids=[evil])


def test_nkjp_words_rejects_traversal_fileid(tmp_path):
    """All NKJP read modes funnel through add_root(); words() must reject too."""
    root = _make_corpus(tmp_path)
    reader = _reader(root)
    evil = os.path.join(str(root), os.pardir, "outside") + os.sep
    with pytest.raises(ValueError):
        reader.words(fileids=[evil])


def test_nkjp_header_rejects_inroot_symlink_escape(tmp_path):
    """A symlink *inside* the corpus root that points outside must be rejected.

    This is the case ``os.path.abspath`` cannot catch: the candidate path is
    lexically in-root, so only resolving the symlink (as ``validate_path``
    does) reveals that it escapes. Skipped where symlinks are unavailable.
    """
    root = _make_corpus(tmp_path)

    secret_dir = tmp_path / "outside"
    secret_dir.mkdir()
    (secret_dir / "header.xml").write_text(_HEADER.format(title="SECRET"))

    link = root / "evil"
    try:
        os.symlink(secret_dir, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    reader = _reader(root)
    # `link` is lexically inside the corpus root, so abspath()-based
    # containment would wrongly allow it; the resolved path is in `outside`.
    evil = str(link) + os.sep
    with pytest.raises(ValueError):
        reader.header(fileids=[evil])
