"""Regression tests for path traversal in FramenetCorpusReader (CWE-22).

``doc()``, ``frame_by_name()`` and ``_lu_file()`` interpolate a caller- or
corpus-supplied name into an XML file path that is then read via
``XMLCorpusView``.  A ``..`` sequence, an absolute path, or a Windows drive/UNC
prefix in that name must be rejected *before* any file is opened, while a
legitimate name must still resolve and read correctly through ``self.abspath()``
(the ``nltk.pathsec`` sandbox).

Paths are built with ``os.path.join`` / ``os.pardir`` so the tests behave the
same on POSIX and Windows.
"""

import builtins
import os

import pytest

from nltk.corpus.reader.framenet import (
    AttrDict,
    FramenetCorpusReader,
    FramenetError,
    _reject_unsafe_path_component,
)

_FRAME_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<frame xmlns="http://framenet.icsi.berkeley.edu" ID="42" name="{name}">\n'
    "<definition>A minimal test frame.</definition>\n"
    "</frame>\n"
)


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


def _record_opens(monkeypatch):
    """Spy on builtin open() so a test can assert nothing outside the corpus
    was ever opened."""
    opened = []
    real_open = builtins.open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    return opened


# --- legitimate flow still works (guards against the abspath() refactor) -------


def test_framenet_frame_reads_legitimate_file(tmp_path):
    """A real in-root frame must still parse after routing through abspath()."""
    root = _make_corpus(tmp_path)
    (root / "frame" / "TestFrame.xml").write_text(_FRAME_XML.format(name="TestFrame"))

    fn = FramenetCorpusReader(str(root), [])
    f = fn.frame("TestFrame")
    assert f.name == "TestFrame"
    assert str(f.ID) == "42"


def test_framenet_allows_normal_frame_name(tmp_path):
    """A normal but absent frame name fails as 'unknown', not 'invalid'."""
    fn = FramenetCorpusReader(str(_make_corpus(tmp_path)), [])
    with pytest.raises(FramenetError) as exc:
        fn.frame("NoSuchFrame")
    assert "Invalid frame name" not in str(exc.value)
    assert "Unknown frame" in str(exc.value)


# --- frame_by_name(): traversal + Windows drive rejection ----------------------


def test_framenet_rejects_traversal_frame_name(tmp_path, monkeypatch):
    """A ../ traversal in the frame name is rejected before any file read."""
    root = _make_corpus(tmp_path)
    secret = tmp_path / "outside"
    secret.mkdir()
    (secret / "pwn.xml").write_text(_FRAME_XML.format(name="pwned"))

    fn = FramenetCorpusReader(str(root), [])
    opened = _record_opens(monkeypatch)
    evil = os.path.join(os.pardir, os.pardir, "outside", "pwn")
    with pytest.raises(FramenetError, match="Invalid frame name"):
        fn.frame(evil)
    assert not any("outside" in p for p in opened), "traversal reached the filesystem"


def test_framenet_rejects_drive_prefixed_frame_name(tmp_path):
    """A Windows drive-qualified name (no separator, no '..') is rejected."""
    fn = FramenetCorpusReader(str(_make_corpus(tmp_path)), [])
    with pytest.raises(FramenetError, match="Invalid frame name"):
        fn.frame("C:evil")


# --- doc(): the fulltext filename comes from the (untrusted) corpus index ------


def test_framenet_doc_rejects_traversal_filename(tmp_path, monkeypatch):
    root = _make_corpus(tmp_path)
    fn = FramenetCorpusReader(str(root), [])
    # Simulate a crafted corpus index whose document filename traverses out.
    evil = os.path.join(os.pardir, os.pardir, "outside", "pwn")
    fn._fulltext_idx = {7: AttrDict({"filename": evil})}

    opened = _record_opens(monkeypatch)
    with pytest.raises(FramenetError, match="Invalid document filename"):
        fn.doc(7)
    assert not any("outside" in p for p in opened), "traversal reached the filesystem"


def test_framenet_doc_rejects_drive_prefixed_filename(tmp_path):
    fn = FramenetCorpusReader(str(_make_corpus(tmp_path)), [])
    fn._fulltext_idx = {7: AttrDict({"filename": "C:evil"})}
    with pytest.raises(FramenetError, match="Invalid document filename"):
        fn.doc(7)


# --- _lu_file(): the LU id comes from corpus data ------------------------------


def test_framenet_lu_file_rejects_traversal_id(tmp_path, monkeypatch):
    root = _make_corpus(tmp_path)
    fn = FramenetCorpusReader(str(root), [])
    lu = AttrDict({"ID": os.path.join(os.pardir, os.pardir, "outside", "SECRET")})

    opened = _record_opens(monkeypatch)
    with pytest.raises(FramenetError, match="Invalid LU id"):
        fn._lu_file(lu)
    assert not any("outside" in p for p in opened), "traversal reached the filesystem"


# --- the validation helper itself ---------------------------------------------


@pytest.mark.parametrize(
    "bad",
    ["../x", "a/b", "a\\b", "..", "C:evil", r"\\host\share\x", "/abs.xml"],
)
def test_reject_unsafe_path_component_blocks(bad):
    with pytest.raises(FramenetError):
        _reject_unsafe_path_component(bad, "frame name")


@pytest.mark.parametrize("ok", ["TestFrame", "Apply_heat", "lu123", "a.b-c"])
def test_reject_unsafe_path_component_allows_normal(ok):
    _reject_unsafe_path_component(ok, "frame name")  # must not raise
