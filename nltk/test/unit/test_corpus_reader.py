import os

import pytest

from nltk.corpus.reader.plaintext import PlaintextCorpusReader
from nltk.corpus.reader.util import find_corpus_fileids
from nltk.data import FileSystemPathPointer


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires os.symlink")
def test_corpusreader_open_blocks_symlink_escape(tmp_path):
    # Arrange: a corpus root in tempdir
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()

    # Arrange: a second directory also in tempdir (so pathsec allowed-roots won't object)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    # Secret file outside the corpus root
    secret = outside_dir / "secret.txt"
    secret.write_text("should not be readable via corpus_root", encoding="utf-8")

    # Create a symlink inside corpus_root that points outside corpus_root
    link = corpus_root / "outside_link"
    os.symlink(str(outside_dir), str(link))

    reader = PlaintextCorpusReader(str(corpus_root), r".*")

    # Act + Assert: opening via the symlinked path must be blocked by corpus-root sandboxing
    with pytest.raises((ValueError, PermissionError, OSError)):
        reader.open("outside_link/secret.txt").read()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires os.symlink")
def test_find_corpus_fileids_skips_symlink_escape(tmp_path):
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()

    inside_file = corpus_root / "inside.txt"
    inside_file.write_text("inside", encoding="utf-8")

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    secret = outside_dir / "secret.txt"
    secret.write_text("secret", encoding="utf-8")

    escaping_link = corpus_root / "outside_link"
    os.symlink(str(outside_dir), str(escaping_link))

    fileids = find_corpus_fileids(FileSystemPathPointer(str(corpus_root)), r".*")

    assert "inside.txt" in fileids
    assert "outside_link/secret.txt" not in fileids
