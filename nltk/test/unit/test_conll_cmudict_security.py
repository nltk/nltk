"""Regression tests for uncaught crashes on a single malformed line in the
CoNLL and CMUdict corpus readers (CWE-20 / improper input validation).

These readers split or index a corpus line without validating its shape, so one
bad line raised an uncaught exception out of a standard public reader method and
aborted iteration over the *whole* corpus:

* ``conll.py`` ``chunked_words``/``chunked_sents`` -- ``chunk_tag.split("-")``
  unpacked into two names, crashing on a tag with no ``-`` (and on a chunk type
  that legitimately contains a ``-``).
* ``conll.py`` ``parsed_sents`` and ``srl_spans`` -- ``tag.split("*")`` unpacked
  into two names, crashing on a tag with no ``*``.
* ``cmudict.py`` ``entries``/``dict``/``words`` -- ``pieces[0]`` on a blank /
  whitespace-only line raised ``IndexError``.

These back the registered ``conll2000``/``conll2002``/``cmudict`` corpora, so the
standard read path is affected. The readers now fail with a clear, catchable
``ValueError`` on a genuinely malformed tag (matching the reader's existing
"Inconsistent number of columns" error), tolerate chunk types that contain a
hyphen, and skip blank CMUdict lines instead of crashing.
"""

import pytest

from nltk.corpus.reader.cmudict import CMUDictCorpusReader
from nltk.corpus.reader.conll import ConllChunkCorpusReader, ConllCorpusReader
from nltk.tree import Tree


def _write(tmp_path, name, text):
    (tmp_path / name).write_text(text, encoding="utf-8")
    return str(tmp_path), [name]


# --------------------------------------------------------------------------
# conll: chunk tags
# --------------------------------------------------------------------------
def test_chunked_words_rejects_malformed_chunk_tag(tmp_path):
    """A chunk tag with no '-' raises a clear ValueError, not a cryptic one."""
    root, fids = _write(tmp_path, "bad.conll", "the DT B-NP\ncat NN BADCHUNK\n\n")
    reader = ConllChunkCorpusReader(root, fids, chunk_types=("NP",))
    with pytest.raises(ValueError, match="Malformed chunk tag"):
        list(reader.chunked_words())


def test_chunked_words_rejects_bad_iob_state_or_empty_type(tmp_path):
    """A tag with an unsupported IOB state or an empty type fails fast."""
    for bad in ("the DT X-NP\n\n", "the DT B-\n\n"):
        root, fids = _write(tmp_path, "bad.conll", bad)
        reader = ConllChunkCorpusReader(root, fids, chunk_types=("NP",))
        with pytest.raises(ValueError, match="Malformed chunk tag"):
            list(reader.chunked_words())


def test_chunked_words_accepts_hyphenated_chunk_type(tmp_path):
    """A chunk type that contains a hyphen must parse, not crash on unpacking."""
    root, fids = _write(tmp_path, "hyp.conll", "the DT B-NP-SBJ\ncat NN I-NP-SBJ\n\n")
    reader = ConllChunkCorpusReader(root, fids, chunk_types=("NP-SBJ",))
    assert list(reader.chunked_words()) == [
        Tree("NP-SBJ", [("the", "DT"), ("cat", "NN")])
    ]


def test_benign_chunked_words_preserved(tmp_path):
    """An ordinary chunked sentence is unchanged."""
    root, fids = _write(tmp_path, "good.conll", "the DT B-NP\ncat NN I-NP\n\n")
    reader = ConllChunkCorpusReader(root, fids, chunk_types=("NP",))
    assert list(reader.chunked_words()) == [Tree("NP", [("the", "DT"), ("cat", "NN")])]


# --------------------------------------------------------------------------
# conll: parse tags
# --------------------------------------------------------------------------
def test_parsed_sents_rejects_malformed_parse_tag(tmp_path):
    """A parse tag with no '*' placeholder raises a clear ValueError."""
    root, fids = _write(tmp_path, "bad.conll", "the DT NOSTAR\n\n")
    reader = ConllCorpusReader(root, fids, ("words", "pos", "tree"))
    with pytest.raises(ValueError, match="Malformed parse tag"):
        list(reader.parsed_sents())


# --------------------------------------------------------------------------
# conll: SRL tags
# --------------------------------------------------------------------------
def test_srl_spans_rejects_malformed_srl_tag(tmp_path):
    """A SRL tag with no '*' placeholder raises a clear ValueError."""
    root, fids = _write(
        tmp_path, "bad.conll", "the DT (S* run NOSTAR\nrun VB *) run (V*)\n\n"
    )
    reader = ConllCorpusReader(
        root, fids, ("words", "pos", "tree", "srl"), srl_includes_roleset=False
    )
    with pytest.raises(ValueError, match="Malformed SRL tag"):
        list(reader.srl_spans())


def test_benign_srl_spans_preserved(tmp_path):
    """Ordinary SRL spans are unchanged."""
    root, fids = _write(
        tmp_path, "good.conll", "the DT (S* - *\nrun VB *) run (V*)\n\n"
    )
    reader = ConllCorpusReader(
        root, fids, ("words", "pos", "tree", "srl"), srl_includes_roleset=False
    )
    assert list(reader.srl_spans()) == [[[((1, 2), "V")]]]


# --------------------------------------------------------------------------
# cmudict: blank lines
# --------------------------------------------------------------------------
def test_cmudict_skips_blank_lines(tmp_path):
    """A blank line between entries is skipped instead of crashing the read."""
    # CMUdict lines are "<word> <counter> <transcription...>"; the reader keeps
    # ``pieces[2:]`` as the pronunciation, so the counter column is included here.
    root, fids = _write(
        tmp_path, "bad.dict", "HELLO 1 HH AH0 L OW1\n   \nWORLD 1 W ER1 L D\n"
    )
    entries = list(CMUDictCorpusReader(root, fids).entries())
    # Both real entries are read in full (the blank line did not abort iteration).
    assert entries == [
        ("hello", ["HH", "AH0", "L", "OW1"]),
        ("world", ["W", "ER1", "L", "D"]),
    ]
