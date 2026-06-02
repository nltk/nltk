import os

import pytest

from nltk.corpus.reader.plaintext import PlaintextCorpusReader


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
