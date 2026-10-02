"""Regression tests for the quadratic-backtracking ReDoS in NLTK's YCOE corpus
reader (``nltk.corpus.reader.ycoe.YCOEParseCorpusReader._parse``) -- CWE-400.

Before parsing a bracketed block, the reader strips ``(CODE ...)`` and
``(ID ...)`` metadata nodes with ``re.sub(r"\\((CODE|ID)[^)]*\\)", "", t)``. On a
crafted block of repeated ``(CODE`` with no closing ``)``, the literal anchor
recurs O(n) times and the ``[^)]*`` run rescans to end-of-line at every anchor
position -- O(n^2) in the block length. ``parsed_sents()`` reaches this helper,
so a single crafted ``.psd`` file could pin a CPU core. This is the same class as
CVE-2021-3828 (comparative_sents reader). The inter-node run is now bounded, so
the substitution is linear; ordinary corpora are stripped identically.
"""

import os
import sys
import traceback

from nltk.corpus.reader.ycoe import YCOEParseCorpusReader

from . import _mp_ctx

# A minimal well-formed YCOE parsed block: a couple of category/word nodes with
# the (CODE ...) and (ID ...) metadata the reader is meant to strip out.
_SAMPLE = (
    "(CODE <T00980000000>)\n"
    "( (IP-MAT (NP-NOM (D^N Se) (N^N cyning)) (VBPI haefd))\n"
    "  (ID coaelive,+ALS_1:1.4))\n"
)


def _reader(tmp_path, text):
    (tmp_path / "f.psd").write_text(text, encoding="utf8")
    return YCOEParseCorpusReader(str(tmp_path), ["f.psd"])


def test_ycoe_code_and_id_nodes_are_stripped(tmp_path):
    """A normal block parses to its tree with (CODE ...)/(ID ...) removed."""
    r = _reader(tmp_path, _SAMPLE)
    parses = [str(t) for t in r.parsed_sents()]
    joined = " ".join(parses)
    assert "CODE" not in joined
    assert "ID" not in joined
    # the linguistic content survives the strip
    assert "cyning" in joined
    assert "VBPI" in joined


def test_ycoe_strip_matches_unbounded_pattern(tmp_path):
    """The bounded substitution is byte-for-byte identical to the old unbounded
    one on representative (short) real CODE/ID nodes."""
    import re

    for block in (
        "(CODE <P_142v>)",
        "(ID coaelhom,+AHom_1:1.4)",
        "(CODE <T00980000000>) ( (IP-MAT (NP x)) (ID coadrian,3.31))",
        "no code or id nodes here at all",
        "(CODE a) (CODE b) (ID c) (IP (NP y))",
    ):
        old = re.sub(r"(?u)\((CODE|ID)[^\)]*\)", "", block)
        new = re.sub(r"(?u)\((CODE|ID)[^\)]{0,400}\)", "", block)
        assert old == new, f"bound changed output on: {block!r}"


def _parsed_worker(root):
    """Read parsed_sents() from a crafted YCOE corpus; exit 0 on success, 3 on
    error. On error the traceback is printed (and stderr flushed, since
    ``os._exit`` skips normal shutdown) so a failure is diagnosable in CI."""
    try:
        list(YCOEParseCorpusReader(root, ["f.psd"]).parsed_sents())
        os._exit(0)
    except BaseException:
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(3)


def test_ycoe_parse_is_linear_not_quadratic(tmp_path):
    """A crafted block of repeated ``(CODE`` with no closing ``)`` must not blow
    up quadratically. Run in a separate process with a hard deadline: the bounded
    substitution returns in milliseconds, while the old unbounded ``[^)]*`` is
    O(n^2) and needs tens of seconds at this size, so a regression is terminated
    and fails instead of pinning a core for the rest of the suite."""
    (tmp_path / "f.psd").write_text("(CODE" * 200_000 + "\n\n", encoding="utf8")

    ctx = _mp_ctx()
    proc = ctx.Process(target=_parsed_worker, args=(str(tmp_path),))
    proc.start()
    proc.join(30)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "YCOEParseCorpusReader.parsed_sents() did not finish in time: "
            "ReDoS regressed"
        )
    assert proc.exitcode == 0, f"worker failed (exit {proc.exitcode})"
