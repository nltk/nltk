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

4. The second sweep, targeting stem/metric/parse sinks the first pass missed:
   LancasterStemmer (per-token rule loop rescans the word each pass, O(len^2)),
   ``metrics.segmentation.ghd`` (O(boundaries^2) DP, unlike its capped
   ``edit_distance`` cousin and its linear ``windowdiff``/``pk`` siblings),
   ``translate.lepor.alignment`` (an earlier CVE cut per-token lookup to O(1)
   but left the repeated-token matching O(n^2)), and
   ``TransitionParser._is_projective`` (list-membership inside a triple loop =
   O(V^4), now a set = O(V^3)).

5. The metrics cluster: ``agreement.AnnotationTask`` (Disagreement/alpha/
   weighted_kappa loop over the distinct label set = O(|K|^2), now a
   distinct-label cap), ``paice.Paice`` (``_calculate`` rescanned every stem
   for every lemma = O(|lemmas|*|stems|), now a word->stem index = linear), and
   ``confusionmatrix.ConfusionMatrix.evaluate`` (precision/recall each scanned a
   full column/row = O(V^2) reporting residual to CVE-2026-12839's O(n)
   constructor, now O(1) via a cached column total beside the row total).

6. The Snowball stemmers (dutch/english/french/german/italian/romanian): the
   "mark interior y/i/u as a consonant" step rebuilt the whole string on each
   match inside a per-position loop = O(n^2) on a crafted token; now an in-place
   list mutation joined once (byte-for-byte identical output).

7. The greedy-token-over-data ReDoS batch: a constant pattern with a greedy
   leading token (\w+, \s*, [^"]+) and an optionally-absent suffix, applied with
   findall/sub/split over attacker data, is O(n^2). ``destructive.py`` (the
   default word_tokenize final-period rule -- a space inside the class abuts
   \s*$), ``reviews.py`` FEATURES (the {0,50} bound missed a spaceless run),
   ``lin.py`` _key_re, ``bracket_parse.py`` ALPINO_ATTR (residual after
   ALPINO_NODE was hardened), ``senseval.py`` lone-& sub, and ``sem/evaluate.py``
   _VAL_SPLIT_RE + siblings (residual after CVE-2026-12890). All routed through
   redos.compile; the regex engine linearizes four, destructive/lin are bounded
   by the wall-clock timeout.

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


class TestLancasterStemmerQuadratic:
    def test_correctness_preserved(self):
        from nltk.stem.lancaster import LancasterStemmer

        st = LancasterStemmer()
        assert [
            st.stem(w)
            for w in ["maximum", "presumably", "multiply", "provision", "saying"]
        ] == ["maxim", "presum", "multiply", "provid", "say"]
        assert LancasterStemmer(strip_prefix_flag=True).stem("kilometer") == "met"
        assert LancasterStemmer(rule_tuple=("ssen4>", "s1t.")).stem("ness") == "nest"

    def test_over_long_token_returned_unstemmed(self):
        # Pre-patch: `__getLastLetter` rescans the word from 0 each pass and a
        # chainable '>' rule runs one pass per two chars, so an all-alpha token
        # is O(len^2) (16k chars ~ 6s, cleanly quadratic). A real word never
        # nears the cap, so an over-long token is returned unstemmed, not hung.
        from nltk.stem.lancaster import MAX_WORD_LEN, LancasterStemmer

        bomb = "a" * 50000
        assert _elapsed(lambda: LancasterStemmer().stem(bomb)) < 1.0
        assert LancasterStemmer().stem(bomb) == bomb
        assert len("a" * MAX_WORD_LEN)  # cap constant is importable


class TestGhdQuadratic:  # nltk.metrics.segmentation.ghd
    def test_correctness_preserved(self):
        from nltk.metrics.segmentation import ghd

        assert ghd("1100100000", "1100010000", 1.0, 1.0, 0.5) == 0.5
        assert ghd("011", "110", 1.0, 1.0, 0.5) == 1.0
        assert ghd("1", "0", 1.0, 1.0, 0.5) == 1.0

    def test_length_is_bounded(self):
        # O(n_ref_boundaries * n_hyp_boundaries) DP over two segmentations; an
        # all-boundary pair makes both O(len) -> O(len^2) time+memory. Capped.
        from nltk.metrics.segmentation import MAX_GHD_INPUT_LEN, ghd

        n = MAX_GHD_INPUT_LEN + 1
        with pytest.raises(ValueError):
            ghd("1" * n, "1" * n)


class TestLeporAlignmentQuadratic:  # nltk.translate.lepor.alignment
    def test_correctness_preserved(self):
        from nltk.translate.lepor import alignment, sentence_lepor

        ref = "the cat sat on the mat".split()
        hyp = "the cat sat on a mat".split()
        assert alignment(ref, hyp) == alignment(ref, hyp)  # deterministic
        assert len(alignment(ref, hyp)) > 0
        score = sentence_lepor([" ".join(ref)], " ".join(hyp))
        assert isinstance(score, list) and 0.0 < score[0] <= 1.0

    def test_repeated_token_bomb_is_bounded(self):
        # An earlier CVE made per-token lookup O(1) but a token repeated R times
        # still yields R candidate positions inspected R times, so a same-token
        # sentence stayed O(len^2) (`"a "*5000` timed out). Work-budgeted now.
        from nltk.translate.lepor import alignment

        bomb = ["a"] * 5000  # 5000*5000 = 25M candidates >> the 4M budget
        with pytest.raises(ValueError):
            alignment(bomb, bomb)

    def test_large_distinct_input_stays_linear(self):
        # Regression guard for the work-budget (not raw-length) choice: many
        # *distinct* tokens have <=1 candidate each, so the aligner is linear and
        # must NOT be rejected -- a blanket length cap would wrongly kill this.
        from nltk.translate.lepor import alignment

        ref = [f"r{i}" for i in range(50000)]
        hyp = [f"h{i}" for i in range(50000)]  # disjoint => 0 candidates
        assert _elapsed(lambda: alignment(ref, hyp)) < 5.0
        assert alignment(ref[:3], ref[:3]) == [1, 2, 3]  # correctness on distinct


class TestTransitionParserProjectivity:  # _is_projective list->set
    def _tp(self):
        from nltk.parse.transitionparser import TransitionParser

        return TransitionParser("arc-standard")

    def _graph(self, lines):
        from nltk.parse.dependencygraph import DependencyGraph

        return DependencyGraph("\n".join(lines), top_relation_label="ROOT")

    def test_correctness_preserved(self):
        tp = self._tp()
        projective = self._graph(
            ["John\tN\t2\tSUBJ", "loves\tV\t0\tROOT", "Mary\tN\t2\tOBJ"]
        )
        assert tp._is_projective(projective) is True
        # crossing arcs 1->3 and 2->4 => non-projective
        crossing = self._graph(
            ["a\tX\t3\tdep", "b\tX\t4\tdep", "c\tX\t0\tROOT", "d\tX\t3\tdep"]
        )
        assert tp._is_projective(crossing) is False

    def test_large_projective_graph_is_bounded(self):
        # Pre-patch: `(k, m) in arc_list` is an O(V) scan inside a triple loop =>
        # O(V^4). A set makes membership O(1) => O(V^3). Nested arcs (all words
        # attach to the last) never early-return, so the full loop runs.
        v = 200
        lines = [f"w{i}\tX\t{v}\tdep" for i in range(1, v)] + [f"w{v}\tX\t0\tROOT"]
        dg = self._graph(lines)
        assert self._tp()._is_projective(dg) is True
        assert _elapsed(lambda: self._tp()._is_projective(dg)) < 10.0


class TestAnnotationTaskLabelQuadratic:  # nltk.metrics.agreement
    def _task(self, n_labels, coders=("c1", "c2")):
        from nltk.metrics.agreement import AnnotationTask

        data = []
        for i in range(n_labels):
            for c in coders:
                data.append((c, f"i{i}", f"L{i}"))  # unique label per item
        return AnnotationTask(data=data)

    def test_correctness_preserved(self):
        from nltk.metrics.agreement import AnnotationTask

        t = AnnotationTask(
            data=[
                ("c1", "i1", "a"),
                ("c2", "i1", "a"),
                ("c1", "i2", "b"),
                ("c2", "i2", "a"),
                ("c1", "i3", "b"),
                ("c2", "i3", "b"),
            ]
        )
        assert round(t.alpha(), 4) == 0.4444
        assert round(t.avg_Ao(), 4) == 0.6667
        assert round(t.weighted_kappa(), 4) == 0.4

    def test_many_distinct_labels_is_bounded(self):
        # Disagreement()/weighted_kappa loop over the distinct label set K, so a
        # task with one unique label per item is O(|K|**2) (CWE-407); |K| is
        # attacker-controlled. Capped on the distinct-label count.
        from nltk.metrics.agreement import MAX_AGREEMENT_LABELS

        with pytest.raises(ValueError):
            self._task(MAX_AGREEMENT_LABELS + 1).alpha()

    def test_large_data_few_labels_stays_linear(self):
        # Regression guard for the distinct-count (not raw-length) choice: 40k
        # items over 2 labels must NOT be rejected (a len(data) cap would kill
        # it) and must stay fast.
        from nltk.metrics.agreement import AnnotationTask

        data = []
        for i in range(40000):
            lab = "yes" if i % 2 else "no"
            data += [("c1", f"i{i}", lab), ("c2", f"i{i}", lab)]
        assert _elapsed(lambda: AnnotationTask(data=data).alpha()) < 5.0


class TestPaiceQuadratic:  # nltk.metrics.paice
    def test_correctness_preserved(self):
        from nltk.metrics.paice import Paice

        lemmas = {
            "kneel": ["kneel", "knelt"],
            "range": ["range", "ranged"],
            "ring": ["ring", "rang", "rung"],
        }
        stems = {
            "kneel": ["kneel"],
            "knelt": ["knelt"],
            "rang": ["rang", "range", "ranged"],
            "ring": ["ring"],
            "rung": ["rung"],
        }
        p = Paice(lemmas, stems)
        assert (p.gumt, p.gdmt, p.gwmt, p.gdnt) == (4.0, 5.0, 2.0, 16.0)
        assert round(p.ui, 3) == 0.8 and round(p.oi, 3) == 0.125

    def test_large_vocab_is_linear(self):
        # `_calculate` rescanned every stem for every lemma => O(|lemmas|*|stems|)
        # plus a per-stem `set(lemmawords)` rebuild. A word->stem index makes it
        # linear (correctness-preserving, so no cap needed on legit large evals).
        from nltk.metrics.paice import Paice

        def build(n):
            return (
                {f"l{i}": [f"w{i}"] for i in range(n)},
                {f"s{i}": [f"w{i}"] for i in range(n)},
            )

        def el(n):
            lem, stm = build(n)
            return _elapsed(lambda: Paice(lem, stm))

        t1, t4 = el(400), el(1600)  # 4x input
        assert t4 < 8 * t1 + 0.5  # linear ~4x, pre-fix O(n^2) ~16x


class TestConfusionMatrixEvaluateQuadratic:  # residual to CVE-2026-12839
    def test_correctness_preserved(self):
        from nltk.metrics import ConfusionMatrix

        ref = "DET NN VB DET JJ NN NN IN DET NN".split()
        test = "DET VB VB DET NN NN NN IN DET NN".split()
        cm = ConfusionMatrix(ref, test)
        assert cm.precision("NN") == 0.75 and cm.recall("NN") == 0.75
        assert cm.evaluate().splitlines()[0].startswith("Tag | Prec.")

    def test_evaluate_all_distinct_is_linear(self):
        # The constructor is O(n) (CVE-2026-12839), but evaluate() scanned all V
        # columns per row -> O(V**2) on an all-distinct matrix. Caching column
        # totals like the existing row-total cache makes it linear.
        from nltk.metrics import ConfusionMatrix

        def el(n):
            r = [f"r{i}" for i in range(n)]
            cm = ConfusionMatrix(r, r)
            return _elapsed(cm.evaluate)

        t1, t4 = el(300), el(1200)  # 4x input
        assert t4 < 8 * t1 + 0.5  # linear ~4x, pre-fix O(V^2) ~16x


class TestSnowballUpcaseQuadratic:  # snowball.py y/i/u "mark-as-consonant" rebuild
    # Six stem() methods upper-cased interior y/i/u via
    # ``word = "".join((word[:i], X, word[i+1:]))`` inside a per-position loop,
    # i.e. O(n) rebuild * O(n) matches = O(n**2) on a crafted token (``"aei"*n``
    # makes every 'i' sit between vowels; a ~0.5 MB token hung ~15s). In-place
    # list mutation makes it linear and is byte-for-byte identical output.
    ANCHORS = {
        "dutch": ("installatie", "installatie"),
        "english": ("generously", "generous"),
        "french": ("quelconque", "quelconqu"),
        "german": ("quellwasser", "quellwass"),
        "italian": ("nazionale", "nazional"),
        "romanian": ("continuare", "continu"),
    }
    TRIGGERS = [
        ("dutch", "aei"),
        ("english", "ay"),
        ("french", "qu"),
        ("german", "aua"),
        ("italian", "aei"),
        ("romanian", "aei"),
    ]

    @pytest.mark.parametrize("lang", list(ANCHORS))
    def test_correctness_preserved(self, lang):
        from nltk.stem.snowball import SnowballStemmer

        w, expected = self.ANCHORS[lang]
        assert SnowballStemmer(lang).stem(w) == expected

    @pytest.mark.parametrize("lang,unit", TRIGGERS)
    def test_upcase_loop_is_linear(self, lang, unit):
        import statistics

        from nltk.stem.snowball import SnowballStemmer

        st = SnowballStemmer(lang).stem

        def med(n):
            return statistics.median(_elapsed(lambda: st(unit * n)) for _ in range(3))

        t1 = med(8000)
        t4 = med(32000)  # 4x input: linear ~4x, pre-fix O(n^2) ~16x
        assert t4 < 8 * t1 + 0.5

    def test_negative_control_langs_stay_linear(self):
        # spanish/portuguese have no rebuild loop; german upcases only u/y (not
        # i). ``"aei"*n`` must stay linear -- a guard against a future change that
        # reintroduces the vulnerable idiom into these.
        from nltk.stem.snowball import SnowballStemmer

        for lang in ("spanish", "portuguese"):
            st = SnowballStemmer(lang).stem
            assert _elapsed(lambda: st("aei" * 40000)) < 2.0


# ==========================================================================
# GREEDY-TOKEN-OVER-DATA ReDoS (fixed) -- constant pattern, attacker data
# ==========================================================================
# Shape: a greedy leading token (\w+, \s*, [^"]+) plus a required suffix that may
# be absent, applied with findall/sub/split over attacker-controlled corpus/text
# data (which retries at every start position) -> O(n^2). Routed through
# redos.compile: four are linearized by the regex engine, one (lin) still
# backtracks and is bounded by the wall-clock TimeoutError.


class TestNLTKWordTokenizerFinalPeriodDoS:  # destructive.py PUNCTUATION[0]
    def test_benign_tokenize_unchanged(self):
        from nltk.tokenize import NLTKWordTokenizer

        s = (
            "Good muffins cost $3.88 (roughly 3,36 euros)\n"
            "in New York.  Please buy me\ntwo of them.\nThanks."
        )
        assert NLTKWordTokenizer().tokenize(s) == [
            "Good", "muffins", "cost", "$", "3.88", "(", "roughly", "3,36",
            "euros", ")", "in", "New", "York.", "Please", "buy", "me", "two",
            "of", "them.", "Thanks", ".",
        ]  # fmt: skip

    def test_final_period_space_run_is_bounded(self, monkeypatch):
        # The class ends with a space directly before \s*$, so [..space..]* and
        # \s* both match the trailing space run and backtrack O(n^2) when the
        # text ends in a non-space, non-class char (~32 KB -> 8s). The regex
        # engine is also quadratic here, so only the timeout bounds it.
        import nltk.redos as redos_mod

        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 0.5)
        from nltk.tokenize import NLTKWordTokenizer

        with pytest.raises(TimeoutError):
            NLTKWordTokenizer().tokenize("a." + " " * 80000 + "!")

    def test_treebank_no_space_class_stays_linear(self):  # BENIGN guard
        # Treebank's twin rule has no space in the class -> disjoint quantifiers.
        from nltk.tokenize import TreebankWordTokenizer

        assert _elapsed(lambda: TreebankWordTokenizer().tokenize("a." + " " * 80000 + "!")) < 2.0


class TestReviewsFeaturesQuadratic:  # reviews.py FEATURES
    def test_benign_features_unchanged(self):
        from nltk.corpus.reader.reviews import FEATURES

        assert FEATURES.findall("great camera[+3] but heavy[-2]") == [
            ("great camera", "+3"),
            ("but heavy", "-2"),
        ]

    def test_spaceless_run_is_linear(self):
        # The {0,50} bound only stopped the space-separated attack; a spaceless
        # bracket-less run stayed O(n^2) via the leading \w+ retried per position.
        import io

        from nltk.corpus.reader.reviews import ReviewsCorpusReader

        rr = ReviewsCorpusReader.__new__(ReviewsCorpusReader)
        assert _elapsed(lambda: rr._read_features(io.StringIO("a" * 200000 + "\n"))) < 5.0


class TestLinThesaurusKeyQuadratic:  # lin.py _key_re -- engine still backtracks
    def test_key_line_is_bounded(self, monkeypatch):
        import nltk.redos as redos_mod

        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 0.5)
        from nltk.corpus.reader.lin import LinThesaurusCorpusReader

        with pytest.raises(TimeoutError):
            LinThesaurusCorpusReader._key_re.sub(r"\1", "(" * 200000)


class TestAlpinoAttrQuadratic:  # bracket_parse.py ALPINO_ATTR
    def test_long_node_body_is_linear(self):
        import nltk.corpus.reader.bracket_parse as bp

        r = bp.AlpinoCorpusReader.__new__(bp.AlpinoCorpusReader)
        doc = '<alpino_ds version="1.3">\n<node ' + "a" * 200000 + ">\n</alpino_ds>\n"
        assert _elapsed(lambda: bp.AlpinoCorpusReader._normalize(r, doc)) < 5.0


class TestSensevalFixXMLQuadratic:  # senseval.py lone-& sub
    def test_lone_amp_whitespace_run_is_linear(self):
        from nltk.corpus.reader.senseval import _fixXML

        assert _elapsed(lambda: _fixXML(" " * 200000)) < 5.0
        assert _fixXML("a & b") == "a &amp; b"  # correctness preserved


class TestEvaluateValSplitQuadratic:  # sem/evaluate.py _VAL_SPLIT_RE + siblings
    def test_internal_whitespace_run_is_linear(self):
        from nltk.sem.evaluate import read_valuation

        assert _elapsed(lambda: read_valuation("a => {" + " " * 200000 + "}")) < 5.0
        assert dict(read_valuation("boy => b1")) == {"boy": "b1"}  # correctness


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
