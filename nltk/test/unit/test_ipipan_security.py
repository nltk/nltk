"""Regression tests for symlink-based path escape in IPIPANCorpusReader
(CWE-22 / CWE-59).

``channels()``, ``domains()``, ``categories()`` and ``fileids(channels=...)``
route through ``_get_tag()``, which used to call the builtin ``open()`` on a
plain string produced by ``.replace("morph.xml", "header.xml")`` on the
result of ``self.abspath()``. Since ``FileSystemPathPointer`` subclasses
``str``, that ``.replace()`` call silently discarded the ``PathPointer``
wrapper, so the resulting ``open()`` never went through ``nltk.pathsec`` at
all, not even the global, non-scoped check. A symlink planted inside the
corpus root, with a name containing no separators or "..", passed the
existing traversal guard cleanly and could point anywhere on the filesystem.

Paths are built with ``os.path.join`` / ``os.pardir`` so the tests behave the
same on POSIX and Windows.
"""

import os

import pytest

from nltk.corpus.reader.ipipan import IPIPANCorpusReader


def _make_corpus(tmp_path):
    root = tmp_path / "ipipan"
    root.mkdir()
    (root / "real_morph.xml").write_text("<tei>legit morph</tei>")
    (root / "real_header.xml").write_text("<channel>legit-channel</channel>")
    return root


def _symlink_or_skip(target, link):
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported in this environment")


def test_ipipan_channels_reads_legitimate_file(tmp_path):
    """A real in-root file must still work after adding the containment check."""
    root = _make_corpus(tmp_path)
    reader = IPIPANCorpusReader(str(root), r".*\.xml")
    assert reader.channels(fileids=["real_morph.xml"]) == ["legit-channel"]


def test_ipipan_channels_rejects_traversal_fileid(tmp_path):
    """A ../ traversal fileid is rejected before any file is opened."""
    root = _make_corpus(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "pwn_header.xml").write_text("<channel>pwned</channel>")

    reader = IPIPANCorpusReader(str(root), r".*\.xml")
    evil = os.path.join(os.pardir, "outside", "pwn_morph.xml")
    with pytest.raises(ValueError, match="Traversal blocked"):
        reader.channels(fileids=[evil])


def test_ipipan_channels_rejects_symlink_escape(tmp_path):
    """A symlink inside the corpus root passes the name guard but must still
    be blocked, even though its own name has no separators or ".."."""
    root = _make_corpus(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "stolen.xml"
    secret.write_text("<channel>TOP-SECRET-DATA-OUTSIDE-CORPUS-ROOT</channel>")

    link = root / "evil_link.xml"
    _symlink_or_skip(secret, link)

    # Constructed the normal way: fileids is a regex, so the reader
    # auto-discovers the symlink exactly as it would a real file.
    reader = IPIPANCorpusReader(str(root), r".*\.xml")
    assert "evil_link.xml" in reader.fileids()

    with pytest.raises(ValueError, match="escapes root"):
        reader.channels(fileids=["evil_link.xml"])


def test_ipipan_domains_rejects_symlink_escape(tmp_path):
    """domains() shares _get_tag() with channels(); confirm it is covered too."""
    root = _make_corpus(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "stolen.xml"
    secret.write_text("<domain>pwned</domain>")

    link = root / "evil_link2.xml"
    _symlink_or_skip(secret, link)

    reader = IPIPANCorpusReader(str(root), r".*\.xml")
    with pytest.raises(ValueError, match="escapes root"):
        reader.domains(fileids=["evil_link2.xml"])


def test_ipipan_categories_rejects_symlink_escape(tmp_path):
    """categories() also shares _get_tag() with channels(); confirm it is
    covered too. It post-processes _parse_header()'s result through
    _map_category(), but the ValueError must fire before that ever runs."""
    root = _make_corpus(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "stolen.xml"
    secret.write_text("<keyTerm>pwned</keyTerm>")

    link = root / "evil_link4.xml"
    _symlink_or_skip(secret, link)

    reader = IPIPANCorpusReader(str(root), r".*\.xml")
    with pytest.raises(ValueError, match="escapes root"):
        reader.categories(fileids=["evil_link4.xml"])


def test_ipipan_fileids_by_channel_rejects_symlink_escape(tmp_path):
    """_list_morph_files_by() (used by fileids(channels=...)) shares the same
    _get_tag() call and must be covered too."""
    root = _make_corpus(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "stolen.xml"
    secret.write_text("<channel>pwned</channel>")

    link = root / "evil_link3.xml"
    _symlink_or_skip(secret, link)

    reader = IPIPANCorpusReader(str(root), r".*\.xml")
    with pytest.raises(ValueError, match="escapes root"):
        reader.fileids(channels=["prasa"])
