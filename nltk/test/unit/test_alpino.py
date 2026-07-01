"""Regression tests for the quadratic-backtracking ReDoS in NLTK's Alpino corpus
reader (``nltk.corpus.reader.bracket_parse.AlpinoCorpusReader._normalize``) --
CWE-1333.

The node-normalization helper turned each Alpino ``<node ...>`` element into
s-expression notation with substitutions that chained several lazy ``.*?`` groups
hunting for trailing literals (``pos="``, ``word="``, ``/>``). On a single long
``<node ...`` line that contained the early anchors but never the trailing
literals, every lazy group rescanned the rest of the line and the engine
redistributed the match across the groups -- O(n^2) in the line length. The
public ``words()``/``tagged_words()``/``tagged_sents()``/``parsed_sents()`` entry
points reach this helper, so a crafted Alpino file could pin a CPU core. Each
``<node>`` is now parsed by extracting its attributes in a single linear scan;
ordinary corpora are read identically.
"""

import multiprocessing
import os
import sys
import traceback

from nltk.corpus.reader.bracket_parse import AlpinoCorpusReader

_SAMPLE = (
    '<alpino_ds version="1.3">\n'
    '  <node begin="0" cat="top" end="3" id="0" rel="top">\n'
    '    <node begin="0" cat="smain" end="3" id="1" rel="--">\n'
    '      <node begin="1" end="2" pos="noun" rel="su" word="hond"/>\n'
    '      <node begin="0" end="1" pos="det" rel="det" word="de"/>\n'
    '      <node begin="2" end="3" pos="verb" rel="hd" word="blaft"/>\n'
    "    </node>\n"
    "  </node>\n"
    "  <sentence>de hond blaft</sentence>\n"
    "</alpino_ds>\n"
)


def _reader(tmp_path, text):
    (tmp_path / "alpino.xml").write_text(text, encoding="ISO-8859-1")
    return AlpinoCorpusReader(str(tmp_path))


def test_alpino_reading_preserved(tmp_path):
    """An ordinary Alpino sentence is read exactly as before."""
    r = _reader(tmp_path, _SAMPLE)
    # words()/tagged_words() use the ordered=True path (sorted by 'begin').
    assert list(r.words()) == ["de", "hond", "blaft"]
    assert list(r.tagged_words()) == [
        ("de", "det"),
        ("hond", "noun"),
        ("blaft", "verb"),
    ]
    assert list(r.tagged_sents()) == [
        [("de", "det"), ("hond", "noun"), ("blaft", "verb")]
    ]
    # parsed_sents() uses the ordered=False path (XML order, nested tree).
    assert [str(t) for t in r.parsed_sents()] == [
        "(top (smain (noun hond) (det de) (verb blaft)))"
    ]


def test_alpino_node_without_pos_or_word_is_skipped(tmp_path):
    """A leaf node missing pos/word contributes nothing, as with the old regex."""
    text = (
        '<alpino_ds version="1.3">\n'
        '  <node begin="0" cat="top" end="1" id="0" rel="top">\n'
        '    <node begin="0" end="1" rel="su"/>\n'
        '    <node begin="0" end="1" pos="noun" rel="hd" word="kat"/>\n'
        "  </node>\n"
        "</alpino_ds>\n"
    )
    r = _reader(tmp_path, text)
    assert list(r.words()) == ["kat"]
    assert list(r.tagged_words()) == [("kat", "noun")]


def test_alpino_malformed_fields_left_unconverted(tmp_path):
    """Nodes whose fields break the old regex shape are left unconverted.

    The old substitutions required ``begin="(\\d+)"`` and ``pos="(\\w+)"``; a
    node with a non-numeric ``begin`` or a ``pos`` containing non-word chars was
    never converted (so it does not appear in the output). The attribute-based
    normalizer keeps those constraints for byte-for-byte compatibility.
    """
    text = (
        '<alpino_ds version="1.3">\n'
        '  <node begin="0" cat="top" end="3" id="0" rel="top">\n'
        '    <node begin="1a" end="2" pos="noun" rel="su" word="hond"/>\n'
        '    <node begin="0" end="1" pos="de-t" rel="det" word="de"/>\n'
        '    <node begin="2" end="3" pos="verb" rel="hd" word="blaft"/>\n'
        "  </node>\n"
        "</alpino_ds>\n"
    )
    r = _reader(tmp_path, text)
    # only the well-formed node survives (non-numeric begin / non-\w pos dropped)
    assert list(r.words()) == ["blaft"]
    assert list(r.tagged_words()) == [("blaft", "verb")]


def _words_worker(root):
    """Read words() from a crafted alpino corpus; exit 0 on success, 3 on error.

    On error the traceback is printed (and stderr flushed, since ``os._exit``
    skips normal shutdown) before exiting so a failure here is diagnosable in CI
    -- the parent process only sees the numeric exit code.
    """
    try:
        list(AlpinoCorpusReader(root).words())
        os._exit(0)
    except BaseException:
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(3)


def test_alpino_normalize_is_linear_not_quadratic(tmp_path):
    """A single long, malformed ``<node ...`` line must not blow up quadratically.

    Run in a spawned process with a hard deadline: the linear normalizer returns
    in milliseconds, while the previous chained-lazy regex is O(n^2) and needs
    well over a minute at this size, so a regression is terminated and fails the
    test instead of pinning a core for the rest of the suite.
    """
    # Early anchors (begin=, many pos=) but never the required word="/ />.
    body = (
        '<alpino_ds version="1.3">\n  <node begin="1" '
        + 'pos="a" ' * 200_000
        + "\n</alpino_ds>\n"
    )
    (tmp_path / "alpino.xml").write_text(body, encoding="ISO-8859-1")

    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_words_worker, args=(str(tmp_path),))
    proc.start()
    proc.join(30)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "AlpinoCorpusReader.words() did not finish in time: ReDoS regressed"
        )
    assert proc.exitcode == 0, f"worker failed (exit {proc.exitcode})"
