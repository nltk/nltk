"""Regression tests for path traversal in FramenetCorpusReader (CWE-22).

``frame(name)`` interpolates the caller-supplied frame name into an XML file
path which is then read with the builtin ``open()`` (via ``XMLCorpusView``),
bypassing the ``CorpusReader.open()`` / ``nltk.pathsec`` sandbox.  A ``..``
sequence in the name must not be allowed to escape the corpus root.
"""

import builtins
import os

import pytest

from nltk.corpus.reader.framenet import FramenetCorpusReader, FramenetError


def _make_corpus(tmp_path):
    root = tmp_path / "framenet"
    for d in ("frame", "fulltext", "lu"):
        (root / d).mkdir(parents=True)
    (root / "frameIndex.xml").write_text(
        '<?xml version="1.0"?><frameIndex></frameIndex>'
    )
    (root / "frRelation.xml").write_text(
        '<?xml version="1.0"?><frameRelations></frameRelations>'
    )
    return root


def test_framenet_rejects_traversal_frame_name(tmp_path):
    """A ../ traversal in the frame name must be rejected before any file read."""
    root = _make_corpus(tmp_path)

    secret_dir = tmp_path / "outside"
    secret_dir.mkdir()
    (secret_dir / "pwn.xml").write_text(
        "<frame ID='1' name='x'><definition>S</definition></frame>"
    )

    fn = FramenetCorpusReader(str(root), [])

    opened = []
    real_open = builtins.open
    builtins.open = lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1]
    try:
        with pytest.raises(FramenetError):
            fn.frame("../../../../../.." + str(secret_dir) + "/pwn")
    finally:
        builtins.open = real_open

    assert not any("outside" in p for p in opened), "traversal reached the filesystem"


def test_framenet_allows_normal_frame_name(tmp_path):
    """A normal frame name must pass validation (and only fail as 'unknown')."""
    root = _make_corpus(tmp_path)
    fn = FramenetCorpusReader(str(root), [])
    # No such frame file exists -> FramenetError("Unknown frame: ..."), NOT the
    # "Invalid frame name" rejection. This proves legitimate lookups still work.
    with pytest.raises(FramenetError) as exc:
        fn.frame("NoSuchFrame")
    assert "Invalid frame name" not in str(exc.value)
