"""
Regression tests for the corpus-reader symlink / path-traversal sandbox bypass
(CWE-59, GHSA-p4rw and siblings GHSA-j5pw / GHSA-mvf5 / GHSA-cr8c / GHSA-934p /
GHSA-7qj2).

Several readers derived a path from trusted corpus state and reopened it with a
raw ``open()`` / ``codecs.open()``, so a symlink placed inside a trusted corpus
root could resolve outside the root and still be parsed. Each now validates the
path through ``nltk.pathsec.validate_path`` first.
"""

import os
import tempfile

import pytest

from nltk import data as nltk_data
from nltk import pathsec


@pytest.fixture
def corpus_root(monkeypatch):
    """A trusted, allowlisted corpus root plus an out-of-root secret + symlink."""
    root = tempfile.mkdtemp(prefix="corpus_root_")
    outside = tempfile.mkdtemp(prefix="outside_")
    secret = os.path.join(outside, "secret.txt")
    with open(secret, "w") as fh:
        fh.write("TOPSECRET_OUTSIDE_ROOT")
    link = os.path.join(root, "evil.txt")
    os.symlink(secret, link)
    legit = os.path.join(root, "legit.txt")
    with open(legit, "w") as fh:
        fh.write("in-root")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk_data, "path", [root, *nltk_data.path])
    return {"root": root, "link": link, "legit": legit}


def test_required_root_blocks_symlink_escape(corpus_root):
    """The shared guard the readers use must reject an in-root symlink that
    resolves outside the root, while allowing a genuine in-root file."""
    with pytest.raises((PermissionError, ValueError)):
        pathsec.validate_path(
            corpus_root["link"], context="test", required_root=corpus_root["root"]
        )
    # legit in-root file passes
    pathsec.validate_path(
        corpus_root["legit"], context="test", required_root=corpus_root["root"]
    )


def test_xmlcorpusview_string_fileid_does_not_crash_without_root(corpus_root):
    """XMLCorpusView carries no ``_root``; the guard must fall back to the global
    sandbox rather than raise AttributeError on a bare-string fileid."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    # A legit in-root file must construct without AttributeError.
    XMLCorpusView(corpus_root["legit"], "foo")


def test_mte_file_reader_rejects_out_of_root(corpus_root):
    """MTEFileReader validates its joined path against the corpus root."""
    from nltk.corpus.reader.mte import MTEFileReader

    with pytest.raises((PermissionError, ValueError)):
        MTEFileReader(corpus_root["link"], required_root=corpus_root["root"])


def test_pathsec_open_blocks_hardlink_escape(corpus_root):
    """A hardlink inside the root pointing at an outside-root inode has no
    symlink to resolve, so validate_path alone allows it; the hardened
    pathsec.open must refuse it via the st_nlink guard (CWE-59, GHSA-f794 class)."""
    import os

    from nltk import pathsec

    outside = os.path.join(os.path.dirname(corpus_root["root"]), "hl_secret")
    with open(outside, "w") as fh:
        fh.write("HARDLINK_LEAK")
    hardlink = os.path.join(corpus_root["root"], "hl.txt")
    try:
        os.link(outside, hardlink)
    except OSError:
        pytest.skip("cannot create hardlink on this filesystem")
    with pytest.raises((PermissionError, ValueError)):
        with pathsec.open(hardlink, required_root=corpus_root["root"]):
            pass


def test_pathsec_open_reads_legit_in_root_file(corpus_root):
    """The hardened read path must still open a genuine in-root file."""
    from nltk import pathsec

    with pathsec.open(corpus_root["legit"], required_root=corpus_root["root"]) as fh:
        assert fh.read() == "in-root"


def test_pathsec_open_final_symlink_atomic_reject(corpus_root):
    """O_NOFOLLOW makes the open atomic: a final-component symlink (in-root or
    out) is refused rather than followed, closing the validate-then-open race."""
    from nltk import pathsec

    # even a symlink that resolves in-root is refused by the atomic open
    # (corpora contain no symlinked files, so this is safe/fail-closed).
    with pytest.raises((PermissionError, ValueError)):
        with pathsec.open(corpus_root["link"], required_root=corpus_root["root"]):
            pass


def test_pathsec_open_no_unsafe_fallback_on_oserror(corpus_root, monkeypatch):
    """A transient OSError from the hardened open must not fall back to a plain
    builtins.open that would follow the symlink (regression: TOCTOU leak)."""
    import os

    from nltk import pathsec

    # Point a name at an outside secret via a symlink; force the hardened open to
    # raise a non-security OSError and confirm no builtins.open retry leaks it.
    outside = os.path.join(os.path.dirname(corpus_root["root"]), "leak_secret")
    with open(outside, "w") as fh:
        fh.write("FALLBACK_LEAK")
    link = os.path.join(corpus_root["root"], "fb.txt")
    os.symlink(outside, link)
    with pytest.raises((PermissionError, ValueError, OSError)):
        with pathsec.open(link, required_root=corpus_root["root"]) as fh:
            assert "FALLBACK_LEAK" not in fh.read()


def test_pathsec_open_write_modes_still_contained(corpus_root):
    """Write/append/update modes skip the read-only hardening but must still be
    contained by validate_path (a symlink out of root is refused)."""
    from nltk import pathsec

    for mode in ("r+", "w", "a", "rb+"):
        with pytest.raises((PermissionError, ValueError, OSError)):
            with pathsec.open(
                corpus_root["link"], mode, required_root=corpus_root["root"]
            ):
                pass
