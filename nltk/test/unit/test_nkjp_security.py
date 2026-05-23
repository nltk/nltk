"""Regression tests for path traversal in NKJPCorpusReader (CWE-22).

The NKJP views build file paths from the caller-supplied ``fileids`` and read
them with the builtin ``open()``, bypassing the ``CorpusReader.open()`` /
``nltk.pathsec`` sandbox.  A ``..`` sequence (or an absolute path) in
``fileids`` must not be allowed to escape the corpus root.
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


def test_nkjp_header_default_fileids_still_works(tmp_path):
    """The legitimate (in-root) flow must keep working after the fix."""
    root = _make_corpus(tmp_path)
    reader = NKJPCorpusReader(root=str(root) + "/", fileids="sample")
    out = reader.header()
    assert out and out[0]["title"] == "IN-ROOT"


def test_nkjp_header_rejects_traversal_fileid(tmp_path):
    """A ../ traversal in fileids must be rejected, not read from disk."""
    root = _make_corpus(tmp_path)

    secret_dir = tmp_path / "outside"
    secret_dir.mkdir()
    (secret_dir / "header.xml").write_text(_HEADER.format(title="SECRET"))

    reader = NKJPCorpusReader(root=str(root) + "/", fileids="sample")
    evil = str(root) + "/../../../../../.." + str(secret_dir) + "/"
    with pytest.raises(ValueError):
        reader.header(fileids=[evil])


def test_nkjp_words_rejects_traversal_fileid(tmp_path):
    """All NKJP read modes funnel through add_root(); words() must reject too."""
    root = _make_corpus(tmp_path)
    reader = NKJPCorpusReader(root=str(root) + "/", fileids="sample")
    evil = str(root) + "/../../../../../../etc/"
    with pytest.raises(ValueError):
        reader.words(fileids=[evil])
