r"""
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
   redos.compile; the regex engine linearizes four, lin is bounded by the
   wall-clock timeout, and destructive is linear since the 2026-10-01 scan.
8. The re-anchored leading runs found by the 2026-10-01 regex scan (bottom of
   this file): the default word tokenizer's final-period rule, the blankline
   tokenizer, the TextTiling paragraph-break scan, the three valuation
   splitters, the relextract demo's ``in`` pattern and toktok's strip pattern.

Tests assert (a) correctness is preserved and (b) a crafted input is bounded --
either linear (ratio/wall-clock) or rejected by an explicit length guard. The
sweep also *cleared* several look-alikes as linear or by-design; those are kept
here as explicit BENIGN cases so a future change that turns one quadratic is
caught.
"""

import io

import pytest

from nltk.corpus.reader.pl196x import TEICorpusView
from nltk.corpus.reader.util import read_sexpr_block
from nltk.corpus.reader.xmldocs import XMLCorpusView
from nltk.stem import PorterStemmer
from nltk.test.unit import timing


def _elapsed(fn):
    """Seconds charged to ``fn``: CPU time when it computed, wall time when it
    waited (see :mod:`nltk.test.unit.timing`)."""
    return timing.charged(fn)


def _assert_subquadratic(op, small, big, factor=8.0, noise_floor=0.1, reps=3):
    """Assert ``op(big)`` (big == 4*small) runs under ``factor`` times ``op(small)``.

    A load-invariant ratio, not an absolute ceiling: a linear op is ~4x, the
    pre-patch O(n**2) ~16x, so factor=8 separates them on any machine. The floor
    is multiplicative (an additive slack would hide a small quadratic). The
    measurement is the suite's shared one: CPU time for a CPU-bound op, the wall
    clock for one that waits, small and big runs alternating, minimum kept.
    """
    # every op here computes (parsers, regexes, tokenizers), so its CPU time is
    # its cost, declared rather than left to the share heuristic
    timing.assert_subquadratic(
        op, small, big, factor, noise_floor, reps, cpu_bound=True
    )


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
        # PARA/SENT/WORD `.*?` findall over many unclosed tags was O(k*n); the
        # shipped patterns bound each body and stop at the next open tag of their
        # kind, so the scan is linear while the unbounded form hits the backstop.
        import nltk.redos as redos_mod
        from nltk import redos
        from nltk.corpus.reader.pl196x import PARA, WORD

        pat = PARA if tag == "<p>" else WORD
        assert (
            "{1,4096}+(?![^<])|<(?!p[ >])){0,16384}?"
            if tag == "<p>"
            else "([^<]{0,1024})"
        ) in pat.pattern
        pat.findall(tag * 60000)  # completes, no TimeoutError
        _assert_subquadratic(lambda n: pat.findall(tag * n), 15000, 60000)

        # the verbatim pre-fix pattern (an unbounded lazy body) on the same trigger
        unbounded = redos.compile(
            r"<p(?: [^>]*){0,1}>(.*?)</p>"
            if tag == "<p>"
            else r"<[wc](?: [^>]*){0,1}>(.*?)</[wc]>"
        )
        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 0.5)
        with pytest.raises(TimeoutError):
            unbounded.findall(tag * 60000)


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

    def test_unclosed_sexpr_is_subquadratic(self, monkeypatch):
        # Pre-patch: an oversized single s-expression is re-parsed from position 0
        # on every fixed-size grow -> O(n^2); exponential read growth makes it O(n).
        # Raise the redos cap so a loaded host cannot trip it on the big linear parse
        # (kept small enough here that even 10x CI slowdown stays well under it).
        import nltk.redos as redos_mod

        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 30)
        _assert_subquadratic(
            lambda n: read_sexpr_block(io.StringIO("(" * n)),
            50_000,
            200_000,
            factor=10.0,
        )


class TestChomskyNormalFormFrontMutation:  # GHSA-r53h: tree.transforms
    """The deque rewrite of the right-factoring loop, plus the width-to-depth
    guard found while expanding it: binarisation turns a node's width into
    depth, so a tree that satisfies Tree.fromstring's MAX_TREE_DEPTH bound
    could still come out as a chain the recursive Tree methods cannot walk
    (CWE-674). The transform refuses that up front, on the exact
    post-transform depth, before mutating anything."""

    @staticmethod
    def _flat(n):
        from nltk.tree import Tree

        return Tree("S", ["w%d" % i for i in range(n)])

    @staticmethod
    def _same(a, b):
        # iterative structural equality: Tree.__eq__ recurses over depth
        from nltk.tree import Tree

        stack = [(a, b)]
        while stack:
            x, y = stack.pop()
            if isinstance(x, Tree) != isinstance(y, Tree):
                return False
            if not isinstance(x, Tree):
                if x != y:
                    return False
                continue
            if x.label() != y.label() or len(x) != len(y):
                return False
            stack.extend(zip(x, y))
        return True

    def test_correctness_preserved(self):
        from nltk.tree import Tree
        from nltk.tree.transforms import chomsky_normal_form

        t = Tree.fromstring("(S (NP I) (VP (V saw) (NP (Det the) (N cat))))")
        chomsky_normal_form(t)
        assert t.label() == "S"
        # Binarisation leaves every production at most binary branching.
        assert all(len(p.rhs()) <= 2 for p in t.productions())

    @pytest.mark.parametrize("factor", ["right", "left"])
    def test_flat_node_is_linear(self, factor, monkeypatch):
        from nltk.tree import tree as treemod
        from nltk.tree.transforms import chomsky_normal_form

        # Pre-patch: the right-factoring loop did nodeCopy.pop(0) per child, an
        # O(1)-should-be front removal that is O(n^2) over a wide flat node. The
        # deque + popleft rewrite is linear and byte-for-byte identical; the
        # left branch pops from the end and must stay linear too. The depth
        # guard is lifted here because these widths exist to measure the loop.
        monkeypatch.setattr(treemod, "MAX_TREE_DEPTH", 10_000)
        _assert_subquadratic(
            lambda n: chomsky_normal_form(self._flat(n), factor=factor),
            1_500,
            6_000,
        )

    @pytest.mark.parametrize("factor", ["right", "left"])
    @pytest.mark.parametrize("horz_markov", [None, 0, 1, 2])
    @pytest.mark.parametrize("vert_markov", [0, 1, 2])
    def test_round_trip_restores_the_tree(self, factor, horz_markov, vert_markov):
        import copy

        from nltk.tree import Tree
        from nltk.tree.transforms import chomsky_normal_form, un_chomsky_normal_form

        shapes = [self._flat(n) for n in (1, 2, 3, 5, 12, 300)] + [
            Tree.fromstring(
                "(S (NP I) (VP (V saw) (NP (Det the) (N cat)) (PP (P with) (NP (Det a) (N scope)))))"
            )
        ]
        for original in shapes:
            work = copy.deepcopy(original)
            chomsky_normal_form(
                work, factor=factor, horzMarkov=horz_markov, vertMarkov=vert_markov
            )
            assert all(len(node) <= 2 for node in work.subtrees())
            un_chomsky_normal_form(work, expandUnary=False)
            assert self._same(work, original)

    def test_transform_itself_is_iterative(self):
        import sys

        from nltk.tree.transforms import chomsky_normal_form

        # a 400-wide node binarises to a 399-deep spine; the transform must
        # not recurse to build it (the agenda is an explicit stack)
        limit = sys.getrecursionlimit()
        sys.setrecursionlimit(120)
        try:
            t = self._flat(400)
            chomsky_normal_form(t)
        finally:
            sys.setrecursionlimit(limit)
        assert len(t) == 2

    def test_width_to_depth_amplification_refused_atomically(self):
        from nltk.tree import tree as treemod
        from nltk.tree.transforms import chomsky_normal_form

        t = self._flat(3000)
        with pytest.raises(ValueError, match="MAX_TREE_DEPTH"):
            chomsky_normal_form(t)
        # refused before any mutation: still flat, still 3000 wide
        assert len(t) == 3000 and t.height() == 2
        assert treemod.MAX_TREE_DEPTH == 500  # the bound the guard reads

    @pytest.mark.parametrize("factor", ["right", "left"])
    def test_exact_boundary_both_factors(self, factor):
        import copy

        from nltk.tree.transforms import chomsky_normal_form

        # a flat node of n children binarises to n - 1 Tree levels (the last
        # child hangs off the end of the chain), so 501 is the last width
        # allowed; Tree.height() counts the leaf as one more level
        allowed = self._flat(501)
        chomsky_normal_form(allowed, factor=factor)
        for walk in (str, lambda t: t.leaves(), lambda t: t.height(), copy.deepcopy):
            walk(allowed)  # every recursive method still works at the bound
        assert allowed.height() == 501
        with pytest.raises(ValueError, match="502 levels deep"):
            chomsky_normal_form(self._flat(503), factor=factor)

    @pytest.mark.parametrize("factor", ["right", "left"])
    def test_nested_widths_compound_by_position(self, factor):
        from nltk.tree import Tree
        from nltk.tree.transforms import chomsky_normal_form

        # every node is well under the bound on its own: the depths add up
        # only where the factoring puts the wide subtree at the deep end of
        # the chain (last child on the right, first child on the left), which
        # is what an exact pre-pass, unlike a per-node width cap, tells apart
        def layered(deep_end_first):
            layer = self._flat(200)
            for name in ("M", "O"):
                filler = ["%s%d" % (name, i) for i in range(199)]
                layer = Tree(
                    name, [layer] + filler if deep_end_first else filler + [layer]
                )
            return layer

        compounding = layered(deep_end_first=(factor == "left"))
        with pytest.raises(ValueError, match="597 levels deep"):
            chomsky_normal_form(compounding, factor=factor)
        shallow_side = layered(deep_end_first=(factor == "right"))
        chomsky_normal_form(shallow_side, factor=factor)  # 201 levels: allowed
        assert all(len(node) <= 2 for node in shallow_side.subtrees())

    def test_bound_override_is_honoured(self, monkeypatch):
        from nltk.tree import tree as treemod
        from nltk.tree.transforms import chomsky_normal_form

        monkeypatch.setattr(treemod, "MAX_TREE_DEPTH", 2_000)
        t = self._flat(1_500)
        chomsky_normal_form(t)
        assert len(t) == 2

    def test_parented_trees_keep_their_existing_type_error(self):
        from nltk.tree import MultiParentedTree, ParentedTree
        from nltk.tree.transforms import chomsky_normal_form

        # pre-existing behaviour, unchanged by the deque rewrite: the loop
        # inserts plain Tree nodes, which a parented tree refuses
        for cls in (ParentedTree, MultiParentedTree):
            with pytest.raises(TypeError, match="Can not insert"):
                chomsky_normal_form(cls.fromstring("(S (A a) (B b) (C c) (D d))"))


# ==========================================================================
# GROW-AND-REPARSE / FRONT-OF-SEQUENCE cluster (fixed): newly swept O(n^2)
# ==========================================================================


class TestCCGLexiconTailReslice:  # GHSA-89p3: ccg.lexicon augParseCategory
    def test_correctness_preserved(self):
        from nltk.ccg.lexicon import fromstring

        lex = fromstring(":- S, N\nDet :: N/N\nthe => Det\n")
        assert str(lex.start()) == "S"
        assert [str(c) for c in lex.categories("the")] == ["(N/N)"]

    def test_long_application_chain_is_linear(self):
        from nltk.ccg.lexicon import fromstring

        # Pre-patch: APP_RE/NEXTPRIM_RE carried a trailing (.*) capture and the
        # parser did rest=rest[1:], rescanning the remainder per operator, so a
        # flat application chain parsed in O(n^2). The cursor rewrite is linear.
        _assert_subquadratic(
            lambda n: fromstring(":- S\nw => S" + "/S" * n + "\n"),
            5_000,
            20_000,
        )

    def test_over_length_category_is_rejected(self):
        from nltk.ccg.lexicon import MAX_PARSE_LEN, fromstring

        # Defense in depth beside the linear-time fix: a category longer than
        # MAX_PARSE_LEN is refused up front rather than parsed.
        huge = "S" + "/S" * MAX_PARSE_LEN
        with pytest.raises(ValueError):
            fromstring(":- S\nw => " + huge + "\n")


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
        # Wall-clock scaling ratio (tokenize's per-token cost has a high enough
        # constant that 8000 is a real measurement, not timer noise). Multiplicative
        # floor, not the old ``+ 0.5`` additive slack, so the bound is tighter here.
        from nltk.tokenize import SyllableTokenizer

        monkeypatch.setattr(SyllableTokenizer, "MAX_TOKEN_LEN", 10**9)
        _assert_subquadratic(
            lambda n: SyllableTokenizer().tokenize("aebcd" * n), 8000, 32000
        )

    def test_direction2_giant_multivowel_token_is_bounded(self):
        # A multi-vowel token passes the early return and reaches the O(n)
        # per-character materialisation; the length guard caps it (CWE-407).
        from nltk.tokenize import SyllableTokenizer

        with pytest.raises(ValueError):
            SyllableTokenizer().tokenize("a" * 5000)

    def test_direction3_cross_token_vowel_accumulation_is_bounded(self):
        # Each token stays within MAX_TOKEN_LEN, but assign_values remembers every
        # distinct unknown char as a vowel on the instance, so a reused tokenizer
        # fed many distinct codepoints grew self.vowels without bound until the
        # joined pattern tripped redos's cap. _MAX_VOWEL_CHARS caps the set.
        import warnings

        from nltk.tokenize import SyllableTokenizer
        from nltk.tokenize.sonority_sequencing import _MAX_VOWEL_CHARS

        ssp = SyllableTokenizer()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for k in range(30):
                base = 0x4E00 + k * 4000
                ssp.tokenize("ae" + "".join(chr(base + i) for i in range(4000)))
        assert len(ssp.vowels) <= _MAX_VOWEL_CHARS
        # Still syllabifies correctly after the flood.
        assert ssp.tokenize("justification") == ["jus", "ti", "fi", "ca", "tion"]


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

    def test_large_vocab_is_linear(self, monkeypatch):
        # `_calculate` rescanned every stem for every lemma => O(|lemmas|*|stems|)
        # plus a per-stem `set(lemmawords)` rebuild. A word->stem index makes it
        # linear (correctness-preserving, so no cap needed on legit large evals).
        #
        # Assert on a DETERMINISTIC operation count -- the number of candidate
        # stems `_calculate` examines -- not wall-clock time: a sub-second timing
        # ratio is a flaky gate on a loaded CI runner. With the word->stem index a
        # disjoint vocabulary examines O(n) candidates (~4x on 4x input); the
        # pre-fix per-lemma full-stems scan examined O(n**2) (~16x).
        from nltk.metrics import paice

        counter = {"n": 0}
        real_cut = paice._calculate_cut

        def counting_cut(lemmawords, word_to_stems, stem_sizes):
            for word in set(lemmawords):
                counter["n"] += len(word_to_stems.get(word, ()))
            return real_cut(lemmawords, word_to_stems, stem_sizes)

        monkeypatch.setattr(paice, "_calculate_cut", counting_cut)

        def visits(n):
            counter["n"] = 0
            lem = {f"l{i}": [f"w{i}"] for i in range(n)}
            stm = {f"s{i}": [f"w{i}"] for i in range(n)}
            paice.Paice(lem, stm)
            return counter["n"]

        v1 = visits(400)
        v4 = visits(1600)  # 4x input
        assert v4 < 8 * v1  # linear ~4x candidate visits; pre-fix full scan ~16x


class TestConfusionMatrixEvaluateQuadratic:  # residual to CVE-2026-12839
    def test_correctness_preserved(self):
        from nltk.metrics import ConfusionMatrix

        ref = "DET NN VB DET JJ NN NN IN DET NN".split()
        test = "DET VB VB DET NN NN NN IN DET NN".split()
        cm = ConfusionMatrix(ref, test)
        assert cm.precision("NN") == 0.75 and cm.recall("NN") == 0.75
        assert cm.evaluate().splitlines()[0].startswith("Tag | Prec.")

    def test_evaluate_all_distinct_is_linear(self, monkeypatch):
        # The constructor is O(n) (CVE-2026-12839), but evaluate() scanned all V
        # columns per row -> O(V**2) on an all-distinct matrix. Caching column
        # totals like the existing row-total cache makes it linear.
        #
        # Assert on a DETERMINISTIC count of matrix-cell reads (__getitem__), not
        # wall-clock time, which is a flaky gate on a loaded CI runner: a linear
        # evaluate does O(V) reads (~4x on 4x input); the pre-fix per-label column
        # scan did O(V**2) (~16x).
        from nltk.metrics import ConfusionMatrix

        counter = {"n": 0}
        real_getitem = ConfusionMatrix.__getitem__

        def counting_getitem(self, key):
            counter["n"] += 1
            return real_getitem(self, key)

        monkeypatch.setattr(ConfusionMatrix, "__getitem__", counting_getitem)

        def reads(n):
            r = [f"r{i}" for i in range(n)]
            cm = ConfusionMatrix(r, r)
            counter["n"] = 0  # count only evaluate()'s cell reads
            cm.evaluate()
            return counter["n"]

        g1 = reads(300)
        g4 = reads(1200)  # 4x input
        assert g4 < 8 * g1  # linear ~4x cell reads; pre-fix O(V^2) ~16x


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
        # Scaling assertion: t(200k) < 8 * t(50k). The linear fix is ~4x, the
        # pre-patch per-match rebuild ~16x (and >20s at 200k); for the slower langs
        # 50k is a real measurement, so this is a machine-independent ratio.
        from nltk.stem.snowball import SnowballStemmer

        st = SnowballStemmer(lang).stem
        _assert_subquadratic(lambda n: st(unit * n), 50_000, 200_000)

    def test_negative_control_langs_stay_linear(self):
        # spanish/portuguese have no rebuild loop; german upcases only u/y (not
        # i). ``"aei"*n`` must stay linear -- a guard against a future change that
        # reintroduces the vulnerable idiom into these.
        from nltk.stem.snowball import SnowballStemmer

        for lang in ("spanish", "portuguese"):
            st = SnowballStemmer(lang).stem
            assert _elapsed(lambda: st("aei" * 40000)) < 2.0


# ==========================================================================
# GREEDY-TOKEN-OVER-DATA ReDoS (fixed): constant pattern, attacker data
# ==========================================================================
# Shape: a greedy leading token (\w+, \s*, [^"]+) plus a required suffix that may
# be absent, applied with findall/sub/split over attacker-controlled corpus/text
# data (which retries at every start position) -> O(n^2). Routed through
# redos.compile: four are linearized by the regex engine, one (lin) still
# backtracks and is bounded by the wall-clock TimeoutError; the destructive
# rule is linear since the 2026-10-01 scan (see the last section).


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

    def test_final_period_space_run_is_linear(self):
        # The class ends with a space directly before \s*$; the two re-split a
        # trailing space run at every length when the text ends in a non-space,
        # non-class char. The run is possessive now, so the rule is linear.
        from nltk.tokenize import NLTKWordTokenizer

        tok = NLTKWordTokenizer()
        _assert_subquadratic(
            lambda n: tok.tokenize("a." + " " * n + "x"), 40000, 160000
        )
        _assert_subquadratic(
            lambda n: tok.tokenize("a." + " " * n + "\tx"), 40000, 160000
        )

    def test_final_period_rule_matches_the_pre_fix_rule(self):
        from nltk.tokenize.destructive import NLTKWordTokenizer

        shipped = NLTKWordTokenizer.PUNCTUATION[0][0].pattern
        assert "*+" in shipped and shipped != _PRE_FIX["destructive"]
        texts = [
            "a.", "a. ", "a.  x", "a.) ", 'a.)" \t', "a. \n", ".", "x.»”’  ",
            "a." + " " * 30 + "x", "a." + " " * 30, "a.)" + " " * 30 + "\t",
            "Thanks.\n", "them.", "x. . ", "a.\t\tx", "a. ) x",
        ]  # fmt: skip
        import re

        _same_results(_PRE_FIX["destructive"], shipped, "sub", texts, re.U)

    def test_pre_fix_final_period_rule_has_teeth(self):
        import re

        _trips_backstop(_PRE_FIX["destructive"], "sub", "a." + " " * 80000 + "x", re.U)

    def test_treebank_no_space_class_stays_linear(self):  # BENIGN guard
        # Treebank's twin rule has no space in the class -> disjoint quantifiers.
        from nltk.tokenize import TreebankWordTokenizer

        assert (
            _elapsed(lambda: TreebankWordTokenizer().tokenize("a." + " " * 80000 + "!"))
            < 2.0
        )


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
        assert (
            _elapsed(lambda: rr._read_features(io.StringIO("a" * 200000 + "\n"))) < 5.0
        )


class TestLinThesaurusKeyQuadratic:  # lin.py _key_re: engine still backtracks
    def test_key_line_is_bounded(self, monkeypatch):
        # The key starts an entry's first line, so the shipped pattern is
        # \A-pinned: one attempt per line, linear. Without the pin it re-anchors
        # at every `(` and still runs into the backstop: the pin is the fix.
        import nltk.redos as redos_mod
        from nltk import redos
        from nltk.corpus.reader.lin import LinThesaurusCorpusReader

        pinned = LinThesaurusCorpusReader._key_re
        assert pinned.pattern.startswith(r"\A")
        assert pinned.sub(r"\1", "(" * 200000) == "(" * 200000
        _assert_subquadratic(lambda n: pinned.sub(r"\1", "(" * n), 50000, 200000)

        unpinned = redos.compile(pinned.pattern[len(r"\A") :])
        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 0.5)
        with pytest.raises(TimeoutError):
            unpinned.sub(r"\1", "(" * 200000)


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


# ==========================================================================
# RE-ANCHORED LEADING RUNS (fixed) -- the regex scan of 2026-10-01
# ==========================================================================
# Shape: a pattern that opens with an unbounded whitespace or class run and is
# applied with sub/split/findall/finditer, so the engine retries that run from
# every position of a run no later literal completes: O(n**2) (CWE-407). The
# redos wall-clock cap only bounded the burn. Each fix pins the run to its start
# (a possessive run, or an optional run taken only when no run character
# precedes it) or commits the backtracking (an atomic group). The verbatim
# pre-fix patterns stay here as the faithfulness oracle and as the teeth.

_PRE_FIX = {
    "destructive": r'([^\.])(\.)([\]\)}>"\'»”’ ]*)\s*$',
    "blankline": r"\s*\n\s*\n\s*",
    "texttiling": r"[ \t\r\f\v]*+\n[ \t\r\f\v]*+\n[ \t\r\f\v]*+",
    "val_split": r"\s*(?<!=)=+>\s*",
    "element_split": r"\s*,\s*",
    "tuples": r"\s*(\([^)]+\))\s*",
    "in_relation": r".*\bin\b(?!\b.+ing)",
    "rstrip": r"\s+$",
}


def _apply(rx, op, text, **kw):
    if op == "sub":
        return rx.sub(r"[\g<0>]", text, **kw)
    if op == "split":
        return rx.split(text, **kw)
    if op == "findall":
        return rx.findall(text, **kw)
    if op == "finditer":
        return [m.span() for m in rx.finditer(text, **kw)]
    if op == "match":
        m = rx.match(text, **kw)
        return None if m is None else (m.span(), m.groups())
    raise ValueError(op)


def _same_results(old, new, op, texts, flags=0):
    """The pre-fix and the shipped pattern agree, result for result."""
    from nltk import redos

    ro, rn = redos.compile(old, flags), redos.compile(new, flags)
    for text in texts:
        assert _apply(ro, op, text) == _apply(rn, op, text), text


def _trips_backstop(old, op, text, flags=0):
    """The pre-fix pattern still runs into a 0.5 s wall-clock cap on ``text``."""
    from nltk import redos

    with pytest.raises(TimeoutError):
        _apply(redos.compile(old, flags), op, text, timeout=0.5)


class TestBlanklineTokenizerLeadingRun:  # tokenize/regexp.py BlanklineTokenizer
    def test_benign_split_unchanged(self):
        from nltk.tokenize import blankline_tokenize

        assert blankline_tokenize("a b\n\nc d\n  \n\te") == ["a b", "c d", "e"]

    def test_space_run_before_a_newline_is_linear(self):
        from nltk.tokenize import blankline_tokenize

        _assert_subquadratic(
            lambda n: blankline_tokenize(" " * n + "\na"), 40000, 160000
        )

    def test_shipped_pattern_matches_the_pre_fix_pattern(self):
        from nltk.tokenize import BlanklineTokenizer

        shipped = BlanklineTokenizer()._pattern
        assert shipped != _PRE_FIX["blankline"]
        texts = [
            "", "a", "\n", "\n\n", " \n \n ", "a\n\nb", "a \n \n b", "\n\n\n\n",
            " \n\n\n\n x", "a\n b", "x" + " " * 30 + "\ny", "x" + " " * 30 + "\n\ny",
            "\t\n\x0b\r\n\x0c\x0b \x0c\n\r\n\x0c\n\r", "a\n\n\nb\n\n\n\nc",
        ]  # fmt: skip
        _same_results(_PRE_FIX["blankline"], shipped, "split", texts)

    def test_pre_fix_pattern_has_teeth(self):
        _trips_backstop(_PRE_FIX["blankline"], "split", " " * 80000 + "\na")


class TestTextTilingParagraphBreakLeadingRun:  # texttiling._mark_paragraph_breaks
    _STOPWORDS = ["the", "a", "of", "and", "to"]

    def _tokenizer(self):
        from nltk.tokenize import TextTilingTokenizer

        return TextTilingTokenizer(stopwords=self._STOPWORDS)

    def test_benign_breaks_unchanged(self):
        tt = self._tokenizer()
        assert tt._mark_paragraph_breaks("x" * 120 + "  \n  \n  " + "y" * 120) == [
            0,
            120,
        ]

    def test_space_run_before_a_newline_is_linear(self):
        tt = self._tokenizer()
        _assert_subquadratic(
            lambda n: tt._mark_paragraph_breaks(" " * n + "\n"), 40000, 160000
        )

    def test_shipped_pattern_matches_the_pre_fix_pattern(self):
        import inspect

        from nltk.tokenize import texttiling

        src = inspect.getsource(texttiling.TextTilingTokenizer._mark_paragraph_breaks)
        shipped = r"(?:(?<![ \t\r\f\v])[ \t\r\f\v]*+)?\n[ \t\r\f\v]*+\n[ \t\r\f\v]*+"
        assert shipped in src
        texts = [
            "", "\n", "\n\n", " \n \n ", "a\n\nb", "a \n \n b", "\n\n\n\n",
            "\t\n\x0b\r\n\x0c\x0b \x0c\n\r\n\x0c\n\r", "x" + " " * 30 + "\ny",
            "x" + " " * 30 + "\n\ny", "\r\x0c \t\n\n\t\x0b\n\n\t aa", "a \n\n \n\n b",
        ]  # fmt: skip
        _same_results(_PRE_FIX["texttiling"], shipped, "finditer", texts)

    def test_pre_fix_pattern_has_teeth(self):
        _trips_backstop(_PRE_FIX["texttiling"], "finditer", " " * 80000 + "\n")


class TestValuationLeadingWhitespaceRuns:  # sem/evaluate.py, the three splitters
    def test_benign_parse_unchanged(self):
        from nltk.sem.evaluate import read_valuation

        val = dict(
            read_valuation("a => b\ngirl => {g1, g2}\nchase => {(b1, g1), (b2, g1)}")
        )
        assert val["a"] == "b"
        assert val["girl"] == {("g1",), ("g2",)}
        assert val["chase"] == {("b1", "g1"), ("b2", "g1")}

    def test_interior_space_run_before_the_separator_is_linear(self):
        from nltk.sem.evaluate import read_valuation

        _assert_subquadratic(
            lambda n: read_valuation("a" + " " * n + "b => c"), 10000, 40000
        )

    def test_interior_space_run_before_a_comma_is_linear(self):
        from nltk.sem.evaluate import read_valuation

        _assert_subquadratic(
            lambda n: read_valuation("s => {a" + " " * n + "b, c}"), 20000, 80000
        )

    def test_interior_space_run_before_an_open_tuple_is_linear(self):
        from nltk.sem.evaluate import read_valuation

        # the trailing `(c` is an unclosed tuple: it is now refused (a
        # ValueError naming MAX_TUPLE_LENGTH) rather than read as a scalar,
        # and the refusal is as linear as the parse
        def refused(n):
            with pytest.raises(ValueError, match="MAX_TUPLE_LENGTH"):
                read_valuation("s => {(a, b)" + " " * n + "(c}")

        _assert_subquadratic(refused, 20000, 80000)
        _assert_subquadratic(
            lambda n: read_valuation("s => {(a, b)" + " " * n + "(c, d)}"), 20000, 80000
        )

    def test_shipped_patterns_match_the_pre_fix_patterns(self):
        from nltk.sem import evaluate as ev

        for key, rx, op, texts in (
            ("val_split", ev._VAL_SPLIT_RE, "split",
             [">=> ==>a>>a", "a => b", "a=>b", "a ==> b", " => ", "a" + " " * 30 + "b=>c",
              "a => b => c", "==>", "a =b> c", "a\t=>\nb"]),
            ("element_split", ev._ELEMENT_SPLIT_RE, "split",
             ["a\na,, ,a,a\t,a a", ",a,\n\ta\na,\n ,aaa", "a, b , c", ",", " , ", "a" + " " * 30 + "b,c",
              "a,,b", " ,a, "]),
            ("tuples", ev._TUPLES_RE, "findall",
             ["(a) (b)", "(a, b)" + " " * 30 + "(c", " (a)  (b) ", "(a)(b)", "x (a) y", "( )",
              "(\t\n\t)(\t )\n", "(a\n,) ( )"]),
        ):  # fmt: skip
            assert rx.pattern != _PRE_FIX[key]
            _same_results(_PRE_FIX[key], rx.pattern, op, texts, rx.flags)
        # The tuple pattern's one deliberate difference: its run excludes the
        # `(` anchor (a crafted paren run is O(n), not O(n*bound)), so a nested
        # `(` ends a candidate tuple; read_valuation refuses such a line anyway.
        from nltk import redos

        nested = [
            ",,((a\t(a\t )\t(\t\n\t)(\t )\n",
            "(( ( )\t(\n\t) (a\n,( )",
            "(a\n,( )",
        ]
        pre_fix = redos.compile(_PRE_FIX["tuples"], ev._TUPLES_RE.flags)
        for text in nested:
            got, old = ev._TUPLES_RE.findall(text), pre_fix.findall(text)
            assert got != old and all("(" not in t[1:] for t in got), (text, got, old)
            assert {t for t in old if "(" not in t[1:]} <= set(got), (text, got, old)

    def test_pre_fix_patterns_have_teeth(self):
        import re

        _trips_backstop(_PRE_FIX["val_split"], "split", " " * 20000 + "a=>b")
        _trips_backstop(_PRE_FIX["element_split"], "split", " " * 60000 + "a,")
        _trips_backstop(_PRE_FIX["tuples"], "findall", " " * 60000 + "(a", re.VERBOSE)


class TestRelextractInRelationLookahead:  # sem/relextract.py in_demo IN pattern
    def test_benign_matches_unchanged(self):
        from nltk.sem.relextract import _IN_RE

        assert _IN_RE.match("based in") is not None
        assert _IN_RE.match("a company in the") is not None
        assert _IN_RE.match("in the making") is None
        assert _IN_RE.match("within") is None

    def test_many_in_before_an_ing_is_linear(self):
        from nltk.sem.relextract import _IN_RE

        _assert_subquadratic(
            lambda n: _IN_RE.match("in " * (n // 3) + "ing"), 40000, 160000
        )

    def test_shipped_pattern_matches_the_pre_fix_pattern(self):
        from nltk.sem.relextract import _IN_RE

        assert _IN_RE.pattern != _PRE_FIX["in_relation"]
        texts = [
            "", "in", "in ing", "in x ing", "a in b", "in in", "bin", "in\ting", "going in",
            "in in ing", "x in y ing z", "in ing in", "inn in", "in-in", "in " * 10 + "ing",
            "in " * 10 + "x", "ing in", "in ing" * 3,
        ]  # fmt: skip
        _same_results(_PRE_FIX["in_relation"], _IN_RE.pattern, "match", texts)

    def test_pre_fix_pattern_has_teeth(self):
        _trips_backstop(_PRE_FIX["in_relation"], "match", "in " * 60000 + "ing")


class TestToktokStripPatternLeadingRun:  # toktok.py RSTRIP (not applied by tokenize)
    def test_tokenize_unchanged_and_linear_on_a_tab_run(self):
        from nltk.tokenize import ToktokTokenizer

        tok = ToktokTokenizer()
        assert tok.tokenize("a\t\tb") == ["a", "&#9;", "&#9;", "b"]
        _assert_subquadratic(lambda n: tok.tokenize("\t" * n + "a"), 40000, 160000)

    def test_rstrip_space_run_is_linear(self):
        from nltk.tokenize import ToktokTokenizer

        rx, repl = ToktokTokenizer.RSTRIP
        _assert_subquadratic(lambda n: rx.sub(repl, " " * n + "a"), 40000, 160000)

    def test_shipped_pattern_matches_the_pre_fix_pattern(self):
        from nltk.tokenize import ToktokTokenizer

        shipped = ToktokTokenizer.RSTRIP[0].pattern
        assert shipped != _PRE_FIX["rstrip"]
        texts = [
            "",
            "a",
            " ",
            "a ",
            "a  \n",
            "a\t\n",
            " a ",
            "a b  ",
            "\n",
            " \n ",
            "a" + " " * 30,
        ]
        _same_results(_PRE_FIX["rstrip"], shipped, "sub", texts)

    def test_pre_fix_pattern_has_teeth(self):
        _trips_backstop(_PRE_FIX["rstrip"], "sub", " " * 80000 + "a")
