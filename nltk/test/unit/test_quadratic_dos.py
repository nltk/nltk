"""
Living-audit regression tests for the algorithmic-complexity DoS cluster
(GHSA-ww6m-cw3f-q94g umbrella -- PorterStemmer; siblings GHSA-vp2x-qp44-57v7
XMLCorpusView, GHSA-8mpw-7fpc-4gqj TEICorpusView, and the newly-found
``read_sexpr_block``). CWE-407 / CWE-400.

Three groups:

1. The original quadratic cluster: each sink ran in O(n^2) on a single crafted
   input on the unpatched code (measured out-of-process: PorterStemmer
   `'y'*20000+'ness'` >20s, TEICorpusView 80k lines = 43s, XMLCorpusView /
   read_sexpr_block clean quadratic doubling curves) and is now linear.

2. The general single-untrusted-input batch found by sweeping the whole repo:
   TweetTokenizer digit backtracking, RIBES residual window, SyllableTokenizer
   (vowelless-syllable list rebuild + oversized token), TextTiling, and the
   CHILDES ``replace=True`` per-word rescans.

3. The two-string distance/alignment family (``edit_distance`` /
   ``edit_distance_align`` / ``jaro_similarity`` in metrics.distance,
   ``aline.align``, ``gale_church.align_blocks``): each builds an O(n*m) DP
   matrix (or, for jaro, an O(n^2) double loop) over two untrusted strings and
   is now length-capped. jaro's earlier CVE-2026-12926 fix cut the inner loop
   O(n^3)->O(n^2) but left the length unbounded; the cap closes that residual.

Tests assert (a) correctness is preserved and (b) a crafted input is bounded --
either linear (ratio/wall-clock) or rejected by an explicit length guard. The
sweep also *cleared* several look-alikes as linear or by-design; those are kept
here as explicit BENIGN cases so a future change that turns one quadratic is
caught.
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
# GENERAL ALGORITHMIC-DoS BATCH (fixed) -- single-untrusted-input O(n^2)
# ==========================================================================


class TestTweetTokenizerDigitDoS:
    def test_benign_tokenize_unchanged(self):
        from nltk.tokenize.casual import TweetTokenizer

        assert TweetTokenizer().tokenize("Hi @u http://x.com :) 555-1234 #tag") == [
            "Hi",
            "@u",
            "http://x.com",
            ":)",
            "555-1234",
            "#tag",
        ]

    def test_digit_run_is_bounded(self, monkeypatch):
        # Pre-patch: the phone sub-pattern backtracks O(n^2) on a digit run
        # (~40 KB → HANG). Now bounded by the regex wall-clock timeout.
        import nltk.redos as redos_mod

        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 0.5)
        from nltk.tokenize.casual import TweetTokenizer

        with pytest.raises(TimeoutError):
            TweetTokenizer().tokenize("1" * 80000)


class TestRibesResidualDoS:
    def test_benign_alignment_and_score(self):
        from nltk.translate.ribes_score import sentence_ribes, word_rank_alignment

        assert word_rank_alignment(["the", "cat"], ["the", "cat"]) == [0, 1]
        assert sentence_ribes([["the", "cat", "sat"]], ["the", "cat", "sat"]) == 1.0

    def test_long_low_cardinality_is_bounded(self):
        # Residual: the window cap = len(reference), so low-cardinality tokens
        # never early-break and the loop runs to n (O(n^2)-O(n^3)). Now capped.
        from nltk.translate.ribes_score import word_rank_alignment

        with pytest.raises(ValueError):
            word_rank_alignment(["a"] * 3000, ["a"] * 3000)


class TestSyllableTokenizerDoS:  # SyllableTokenizer -- has MULTIPLE directions
    def test_benign_syllabification_unchanged(self):
        from nltk.tokenize import SyllableTokenizer

        assert SyllableTokenizer().tokenize("justification") == [
            "jus",
            "ti",
            "fi",
            "ca",
            "tion",
        ]
        assert SyllableTokenizer().tokenize("foobar") == ["foo", "bar"]

    def test_low_vowel_run_is_linear_and_unbounded(self):
        # A run with <=1 vowel (e.g. a long digit string) hits the O(n) early
        # return *before* the length guard, so it must still succeed unchanged.
        # This is the regression guard for the guard-placement bug: a blanket
        # length check at the top of tokenize() wrongly rejected `'9'*10000`.
        from nltk.tokenize import SyllableTokenizer

        text = "9" * 10000
        assert SyllableTokenizer().tokenize(text) == [text]

    def test_direction1_vowelless_syllables_are_linear(self, monkeypatch):
        # Pre-patch: `validate_syllables` rebuilt the whole list
        # (`valid_syllables[:-1] + [...]`) for every vowelless syllable, so a
        # token like 'aebcd'*n cost O(n^2). In-place merge makes it linear.
        #
        # This is a wall-clock ratio test, so it must be robust to CI timing
        # noise: (1) a base size large enough that a single tokenize is well
        # above timer resolution (a 4000-rep base measured ~0.01s -- noise
        # dominated -- and made the ratio explode on a free-threaded runner); and
        # (2) the MEDIAN of a few runs, robust to both a fast and a slow outlier.
        # Linear -> t4 ~ 4*t1; the pre-fix O(n^2) -> t4 ~ 16*t1, so an 8x
        # threshold separates them with wide margin.
        import statistics

        from nltk.tokenize import SyllableTokenizer

        monkeypatch.setattr(SyllableTokenizer, "MAX_TOKEN_LEN", 10**9)

        def _median(n):
            return statistics.median(
                _elapsed(lambda: SyllableTokenizer().tokenize("aebcd" * n))
                for _ in range(3)
            )

        t1 = _median(8000)
        t4 = _median(32000)  # 4x the input
        assert t4 < 8 * t1 + 0.5

    def test_direction2_giant_multivowel_token_is_bounded(self):
        # A multi-vowel token passes the early return and reaches the O(n)
        # per-character materialisation; the length guard caps it (CWE-407).
        from nltk.tokenize import SyllableTokenizer

        with pytest.raises(ValueError):
            SyllableTokenizer().tokenize("a" * 5000)


class TestDistanceQuadraticDoS:  # nltk.metrics.distance -- edit_distance + jaro
    def test_benign_results_unchanged(self):
        from nltk.metrics import distance

        assert distance.edit_distance("kitten", "sitting") == 3
        assert distance.edit_distance("rain", "shine") == 3
        assert distance.edit_distance_align("rain", "shine") == [
            (0, 0),
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (4, 5),
        ]
        assert round(distance.jaro_similarity("MARTHA", "MARHTA"), 4) == 0.9444
        assert distance.jaro_similarity("", "") == 1.0

    def test_edit_distance_length_is_bounded(self):
        # O(n*m) time AND memory over two args: `edit_distance("a"*40000,
        # "b"*40000)` allocates tens of GB and runs for hours. Now length-capped.
        from nltk.metrics import distance

        n = distance.MAX_DISTANCE_INPUT_LEN + 1
        with pytest.raises(ValueError):
            distance.edit_distance("a" * n, "b" * n)

    def test_edit_distance_align_length_is_bounded(self):
        from nltk.metrics import distance

        n = distance.MAX_DISTANCE_INPUT_LEN + 1
        with pytest.raises(ValueError):
            distance.edit_distance_align("a" * n, "b" * n)

    def test_jaro_length_is_bounded(self):
        # CVE-2026-12926 fixed jaro's inner loop O(n^3)->O(n^2) but left the
        # length unbounded, so two long near-matching strings stayed a quadratic
        # DoS. The length cap closes that residual.
        from nltk.metrics import distance

        n = distance.MAX_DISTANCE_INPUT_LEN + 1
        with pytest.raises(ValueError):
            distance.jaro_similarity("a" * n, "b" * n)

    def test_asymmetric_long_arg_is_bounded(self):
        # The cap keys off the *longest* arg, so a short-vs-huge call (which still
        # allocates an O(n) matrix row-count over the huge side) is caught too.
        from nltk.metrics import distance

        with pytest.raises(ValueError):
            distance.edit_distance("a", "b" * (distance.MAX_DISTANCE_INPUT_LEN + 1))


class TestAlineQuadraticDoS:  # nltk.metrics.aline.align
    def test_benign_alignment_unchanged(self):
        pytest.importorskip("numpy")
        from nltk.metrics import aline

        # sibling of jaro in the same distance family; align two short words.
        assert len(aline.align("driy", "tres")) > 0

    def test_length_is_bounded(self):
        pytest.importorskip("numpy")
        from nltk.metrics import aline

        n = aline.MAX_ALIGN_INPUT_LEN + 1
        with pytest.raises(ValueError):
            aline.align("a" * n, "a" * n)


class TestGaleChurchQuadraticDoS:  # nltk.translate.gale_church.align_blocks
    def test_benign_alignment_unchanged(self):
        from nltk.translate.gale_church import align_blocks

        assert align_blocks([5, 5, 5], [7, 7, 7]) == [(0, 0), (1, 1), (2, 2)]
        assert align_blocks([10, 5, 5], [12, 20]) == [(0, 0), (1, 1), (2, 1)]

    def test_block_count_is_bounded(self):
        # `backlinks[(i, j)]` is stored for every cell and never pruned, so two
        # texts split into many tiny "sentences" cost O(n*m) time+memory.
        from nltk.translate.gale_church import MAX_ALIGN_BLOCKS, align_blocks

        with pytest.raises(ValueError):
            align_blocks([5] * (MAX_ALIGN_BLOCKS + 1), [5] * 10)


class TestTextTilingDoS:
    def test_oversized_document_is_bounded(self):
        from nltk.tokenize import TextTilingTokenizer

        with pytest.raises(ValueError):
            TextTilingTokenizer().tokenize("x" * 2_000_000)


class TestChildesReplaceDoS:
    def _write(self, tmp_path, nwords):
        ns = "http://www.talkbank.org/ns/talkbank"
        ws = "".join(f"<w>w{i}</w>" for i in range(nwords))
        p = tmp_path / f"c{nwords}.xml"
        p.write_text(
            f'<?xml version="1.0"?><CHAT xmlns="{ns}"><u who="CHI">{ws}</u></CHAT>'
        )
        return p.name

    def test_replace_true_is_linear(self, tmp_path):
        # Pre-patch: per-word `xmlsent.find(...)` rescans the whole utterance =>
        # O(words^2). Now hoisted out of the loop.
        from nltk.corpus.reader import CHILDESCorpusReader

        name = self._write(tmp_path, 8000)
        reader = CHILDESCorpusReader(str(tmp_path), name)
        assert _elapsed(lambda: reader.words(name, replace=True)) < 5.0
        assert len(reader.words(name, replace=True)) == 8000


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

    def test_edit_distance_short_inputs_unaffected(self):
        # `edit_distance` is O(n*m) over two args; it is now length-capped (see
        # TestDistanceQuadraticDoS), but ordinary short inputs are untouched.
        from nltk.metrics import edit_distance

        assert edit_distance("kitten", "sitting") == 3

    def test_skipgrams_blowup_is_by_parameter_not_input(self):
        # `skipgrams` is linear in the sequence; the combinatorial blowup is via
        # the `k` PARAMETER, not the untrusted sequence, so it is by-design.
        from nltk.util import skipgrams

        seq = list(range(20000))
        assert _elapsed(lambda: list(skipgrams(seq, 2, 2))) < 5.0
