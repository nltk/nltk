"""
Living-audit regression tests for the quadratic-complexity DoS cluster
(GHSA-ww6m-cw3f-q94g umbrella -- PorterStemmer; siblings GHSA-vp2x-qp44-57v7
XMLCorpusView, GHSA-8mpw-7fpc-4gqj TEICorpusView, and the newly-found
``read_sexpr_block``). CWE-407.

Each exploitable sink ran in O(n^2) on a single crafted input on the unpatched
code (measured out-of-process: PorterStemmer `'y'*20000+'ness'` >20s,
TEICorpusView 80k lines = 43s, XMLCorpusView / read_sexpr_block clean quadratic
doubling curves). Each is now linear. The tests assert (a) correctness is
preserved and (b) a large crafted input finishes far inside a bound that the old
quadratic would blow past. Sizes are chosen so linear << bound << quadratic.

The cluster sweep also *cleared* several look-alikes as linear or by-design;
those are kept here as explicit BENIGN cases so a future change that turns one
quadratic is caught.
"""

import io
import time

import pytest

from nltk.corpus.reader.pl196x import TEICorpusView
from nltk.corpus.reader.util import read_sexpr_block
from nltk.corpus.reader.xmldocs import XMLCorpusView
from nltk.stem import PorterStemmer


def _elapsed(fn):
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


# ==========================================================================
# EXPLOITABLE (fixed) -- quadratic pre-patch, linear now
# ==========================================================================


class TestPorterStemmerQuadratic:  # GHSA-ww6m
    def test_correctness_preserved(self):
        p = PorterStemmer()
        assert [
            p.stem(w) for w in ["ponies", "caresses", "happy", "sky", "syzygy"]
        ] == [
            "poni",
            "caress",
            "happi",
            "sky",
            "syzygi",
        ]

    def test_consonant_flags_match_is_consonant(self):
        import random

        p = PorterStemmer()
        random.seed(0)
        for _ in range(500):
            w = "".join(
                random.choice("abcdefghijklmnopqrstuvwxyy")
                for _ in range(random.randint(1, 40))
            )
            assert p._consonant_flags(w) == [
                p._is_consonant(w, i) for i in range(len(w))
            ]

    def test_long_y_run_is_linear(self):
        # Pre-patch: `_measure` calls the O(run) `_is_consonant` per position on
        # a run of 'y's -> O(n^2) (`'y'*20000+'ness'` was >20s). Linear now.
        assert _elapsed(lambda: PorterStemmer().stem("y" * 40000 + "ness")) < 8.0


class TestXMLCorpusViewQuadratic:  # GHSA-vp2x
    def test_benign_fragment_unchanged(self):
        v = XMLCorpusView.__new__(XMLCorpusView)
        assert v._read_xml_fragment(io.StringIO("<a>hi</a>")) == "<a>hi</a>"
        assert (
            v._read_xml_fragment(io.StringIO("<a><b>x</b></a>z")) == "<a><b>x</b></a>z"
        )

    def test_giant_unterminated_tag_is_linear(self):
        # Pre-patch: `_VALID_XML_RE.match(fragment)` re-scans the whole growing
        # buffer every 1 KiB block for a single oversized tag -> O(n^2).
        v = XMLCorpusView.__new__(XMLCorpusView)
        payload = io.StringIO("<a " + "x" * 2_000_000 + ">")
        assert _elapsed(lambda: v._read_xml_fragment(payload)) < 5.0


class TestTEICorpusViewQuadratic:  # GHSA-8mpw -- has MULTIPLE quadratic directions
    def _view(self, textids=None):
        v = TEICorpusView.__new__(TEICorpusView)
        v._pagesize = 4096
        v._textids = textids
        v._tagged = False
        v._group_by_sent = False
        return v

    def test_direction1_no_closing_tag_is_linear(self):
        # `block.count(...)` over the whole growing block per line; a file with
        # no '</text>' swallows everything at O(n^2) (80k lines=43s pre-patch).
        payload = io.StringIO("x\n" * 80000)
        assert _elapsed(lambda: self._view().read_block(payload)) < 8.0

    def test_direction2_textid_filter_loop_is_linear(self):
        # `block.find(tid)` + string rebuild per unwanted <text> element was
        # O(k*n); now a single forward pass.
        body = "".join(f'<text id="t{i}">x</text>' for i in range(80000))
        v = self._view(textids={"zzz"})  # filter set that keeps nothing
        assert _elapsed(lambda: v.read_block(io.StringIO(body))) < 8.0

    @pytest.mark.parametrize("tag", ["<p>", "<w>"])
    def test_direction3_lazy_regex_is_bounded(self, tag, monkeypatch):
        # PARA/SENT/WORD `.*?` findall over many unclosed tags is O(k*n) and is
        # not linearised by the regex engine, so it is bounded by the redos
        # wall-clock backstop instead of hanging.
        import nltk.redos as redos_mod

        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 0.5)
        from nltk.corpus.reader.pl196x import PARA, WORD

        pat = PARA if tag == "<p>" else WORD
        with pytest.raises(TimeoutError):
            pat.findall(tag * 60000)


class TestReadSexprBlockQuadratic:
    def test_correctness_preserved(self):
        assert read_sexpr_block(io.StringIO("(a (b c)) (d e)")) == [
            "(a (b c))",
            "(d e)",
        ]
        assert read_sexpr_block(io.StringIO("foo bar (x y)")) == ["foo", "bar", "(x y)"]
        assert read_sexpr_block(io.StringIO("# c\n(a b)"), comment_char="#") == [
            "(a b)"
        ]

    def test_unclosed_sexpr_is_subquadratic(self):
        # Pre-patch: an oversized single s-expression is re-parsed from position
        # 0 on every fixed-size grow -> O(n^2). Exponential read growth makes it
        # O(n). A ratio test is robust to the (high) linear constant: 4x input
        # should cost ~4x (linear), not ~16x (quadratic).
        t1 = _elapsed(lambda: read_sexpr_block(io.StringIO("(" * 200_000)))
        t4 = _elapsed(lambda: read_sexpr_block(io.StringIO("(" * 800_000)))
        assert t4 < 10 * t1 + 0.5


# ==========================================================================
# CLEARED BY THE SWEEP (benign) -- linear or by-design, kept as guards
# ==========================================================================


class TestClearedLinearOrByDesign:
    def test_align_tokens_is_linear(self):
        # `sentence.index(token, point)` with a monotonically advancing point =>
        # linear (public via TreebankWordTokenizer.span_tokenize).
        from nltk.tokenize.util import align_tokens

        toks = ["a"] * 50000
        assert _elapsed(lambda: align_tokens(toks, "a" * 50000)) < 5.0

    def test_read_blankline_block_is_linear(self):
        # `s += line` on a growing block is CPython in-place amortized-linear.
        from nltk.corpus.reader.util import read_blankline_block

        assert _elapsed(lambda: read_blankline_block(io.StringIO("x\n" * 100000))) < 5.0

    def test_edit_distance_is_by_design(self):
        # O(n*m) over TWO explicit args is opt-in algorithmic cost, not a
        # single-input DoS. Documented here; just assert correctness.
        from nltk.metrics import edit_distance

        assert edit_distance("kitten", "sitting") == 3
