# Natural Language Toolkit: corpus-reader path traversal / symlink escape
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Corpus readers must not read outside their own root.

This maps to a cluster of published advisories: CVE-2026-0847 (WordList /
Tagged / Bracket readers concatenating fileids), CVE-2026-12072 (NKJP header /
raw), CVE-2026-12074 / -62384 (Framenet frame files via traversal and symlink),
and CVE-2026-70626 (CorpusReader.open symlink). A caller-supplied fileid must
stay inside the corpus whether it is a ``..`` path, an absolute path, or a
symlink planted inside the corpus that points out of it.
"""

import os
import shutil
import tempfile

import pytest

import nltk.data
from nltk import pathsec

_SECRET = "root:x:0:0:SECRET"


@pytest.fixture
def corpus_and_outside(monkeypatch):
    base = tempfile.mkdtemp(prefix=".nltk_corpus_", dir=os.path.expanduser("~"))
    corpus = os.path.join(base, "corpus")
    outside = os.path.join(base, "outside")
    os.makedirs(corpus)
    os.makedirs(outside)
    with open(os.path.join(outside, "SECRET"), "w") as handle:
        handle.write(_SECRET)
    with open(os.path.join(corpus, "real.txt"), "w") as handle:
        handle.write("hello world")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [base])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield corpus, outside
    finally:
        shutil.rmtree(base, ignore_errors=True)


@pytest.mark.parametrize(
    "reader_name, method",
    [
        ("WordListCorpusReader", "words"),
        ("PlaintextCorpusReader", "raw"),
        ("TaggedCorpusReader", "words"),
    ],
)
@pytest.mark.parametrize(
    "fileid",
    ["../../outside/SECRET", "/etc/passwd", "../../../etc/passwd"],
    ids=["traversal", "absolute", "deep-traversal"],
)
def test_reader_fileid_cannot_escape(corpus_and_outside, reader_name, method, fileid):
    from nltk.corpus import reader as reader_module

    corpus, _outside = corpus_and_outside
    reader_cls = getattr(reader_module, reader_name)
    reader = reader_cls(corpus, r".*\.txt")
    with pytest.raises((PermissionError, ValueError)):
        result = getattr(reader, method)(fileid)
        text = "".join(result) if hasattr(result, "__iter__") else str(result)
        assert _SECRET not in text


def test_a_symlink_fileid_cannot_escape(corpus_and_outside):
    from nltk.corpus import WordListCorpusReader

    corpus, outside = corpus_and_outside
    os.symlink(os.path.join(outside, "SECRET"), os.path.join(corpus, "evil.txt"))
    reader = WordListCorpusReader(corpus, r".*\.txt")
    with pytest.raises((PermissionError, ValueError)):
        text = "".join(reader.words("evil.txt"))
        assert _SECRET not in text


def test_corpusreader_open_refuses_a_symlink_out(corpus_and_outside):
    from nltk.corpus.reader.api import CorpusReader

    corpus, outside = corpus_and_outside
    os.symlink(os.path.join(outside, "SECRET"), os.path.join(corpus, "link.txt"))
    reader = CorpusReader(corpus, [r".*"])
    with pytest.raises((PermissionError, ValueError)):
        reader.open("link.txt").read()


def test_nkjp_header_and_raw_cannot_escape(corpus_and_outside):
    from nltk.corpus.reader.nkjp import NKJPCorpusReader

    corpus, _outside = corpus_and_outside
    for fileid in ("../../outside/SECRET", "/etc/passwd"):
        with pytest.raises((PermissionError, ValueError)):
            reader = NKJPCorpusReader(corpus, fileids=fileid)
            reader.header()


def test_framenet_validate_in_root_is_the_choke_point(corpus_and_outside):
    """Every Framenet frame/lu/doc load funnels through _validate_in_root; it
    must refuse a symlink out, a traversal and an absolute path."""
    from nltk.corpus.reader.framenet import _validate_in_root

    corpus, outside = corpus_and_outside
    os.makedirs(os.path.join(corpus, "frame"))
    symlink = os.path.join(corpus, "frame", "evil.xml")
    os.symlink(os.path.join(outside, "SECRET"), symlink)
    for path in (
        symlink,
        os.path.join(corpus, "frame", "..", "..", "outside", "SECRET"),
        os.path.join(outside, "SECRET"),
    ):
        with pytest.raises((PermissionError, ValueError)):
            _validate_in_root(path, corpus, "test")
    # over-block control: an in-root path is accepted
    good = os.path.join(corpus, "frame", "good.xml")
    _validate_in_root(good, corpus, "test")


def test_the_real_file_still_reads(corpus_and_outside):
    """Over-block control: the whole reader is useless if it refuses its own
    files."""
    from nltk.corpus import WordListCorpusReader

    corpus, _outside = corpus_and_outside
    # WordListCorpusReader.words() yields whole lines, one per entry.
    assert WordListCorpusReader(corpus, r".*\.txt").words("real.txt") == ["hello world"]
