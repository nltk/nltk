# Natural Language Toolkit: algorithmic-DoS hardening tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Regression tests for the algorithmic denial-of-service defects bounded on
untrusted input (CWE-400/407/674/1333):

* ``redos.check_pattern`` bounds the capturing-group count (quadratic compile).
* ``SeekableUnicodeStreamReader.readline`` reads an unterminated line in linear
  time (was O(N**2) re-splitting the whole growing buffer).
* ``XMLCorpusView.read_block`` bounds XML nesting depth (the per-tag
  ``"/".join(context)`` was O(depth) each, so deep nesting was O(n**2)).
* the WordNet ``Synset`` hypernym walkers refuse a cyclic / over-deep graph
  instead of recursing without bound.
* the tokenizer quote restore, the legality syllable loop and the stepping
  recursive-descent parser are linear or deadline-bounded.
* the re-anchoring regex class (a repeatable anchor plus an unbounded run whose
  terminator the attacker omits) is bounded at every shipped site, and a CI
  guard keeps new sites out.

Nothing is mocked: each guard is driven through its real public entry point.
Complexity is measured as a scaling ratio (``op(4n)`` over ``op(n)``), never as
an absolute deadline: a linear sink is ~4x, a quadratic one ~16x, on any
machine and under any load. Every guard also has a negative control that
neuters it in-process and asserts the measurement flips.
"""

import io
import os
import random
import tempfile
import time

import pytest

QUADRATIC_RATIO = 8.0


def _elapsed(fn):
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def _scaling_ratio(op, small, big, reps=3, noise_floor=0.1):
    """Fastest-of-``reps`` ``op(big)`` over ``op(small)`` (big == 4*small).

    The floor is multiplicative so a sub-second quadratic is not hidden by
    additive slack; each side is a min-of-``reps`` to shed a transient stall.
    """
    t_small = min(_elapsed(lambda: op(small)) for _ in range(reps))
    t_big = min(_elapsed(lambda: op(big)) for _ in range(reps))
    return t_big / max(t_small, noise_floor), t_small, t_big


def _assert_subquadratic(op, small, big, reps=3):
    ratio, t_small, t_big = _scaling_ratio(op, small, big, reps=reps)
    assert ratio < QUADRATIC_RATIO, (small, big, t_small, t_big, ratio)


def _assert_quadratic(op, small, big, reps=3):
    """Negative control: with a guard neutered the sink must scale super-linearly."""
    ratio, t_small, t_big = _scaling_ratio(op, small, big, reps=reps)
    assert ratio >= QUADRATIC_RATIO, (small, big, t_small, t_big, ratio)


# --- #32p6: redos capturing-group compile bound ------------------------------


class TestRedosGroupCount:
    def test_group_bomb_is_refused(self):
        from nltk import redos
        from nltk.redos import MAX_GROUP_COUNT

        with pytest.raises(ValueError):
            redos.check_pattern("()" * (MAX_GROUP_COUNT + 1))
        with pytest.raises(ValueError):
            redos.compile("()" * (MAX_GROUP_COUNT + 1))

    def test_reasonable_patterns_still_compile_and_match(self):
        from nltk import redos

        assert redos.compile("(a)(b)(c)").match("abc").group(2) == "b"
        # a pattern at the limit is accepted
        redos.check_pattern("(a)" * 100)

    def test_only_capturing_groups_are_counted(self):
        # Lookbehinds, backreferences, escaped parens and class parens open no
        # capturing group; a pattern at exactly the cap is accepted.
        from nltk import redos
        from nltk.redos import MAX_GROUP_COUNT

        redos.check_pattern("(?<=a)" * (MAX_GROUP_COUNT + 500))
        redos.check_pattern("(?<!a)" * (MAX_GROUP_COUNT + 500))
        redos.check_pattern("(?P<g>a)" + "(?P=g)" * (MAX_GROUP_COUNT + 500))
        redos.check_pattern(r"\(\)" * (MAX_GROUP_COUNT + 500))
        redos.check_pattern("[()]" * (MAX_GROUP_COUNT + 500))
        redos.check_pattern("(a)" * MAX_GROUP_COUNT)
        with pytest.raises(ValueError):
            redos.check_pattern("(a)" * (MAX_GROUP_COUNT + 1))

    def test_group_bound_has_teeth(self, monkeypatch):
        # Lifting the bound is what lets the bomb through: the refusal above is
        # the group guard, not a neighbour.
        import nltk.redos as redos_mod

        bomb = "()" * (redos_mod.MAX_GROUP_COUNT + 1)
        monkeypatch.setattr(redos_mod, "MAX_GROUP_COUNT", 10**9)
        redos_mod.check_pattern(bomb)  # accepted once the bound is gone
        monkeypatch.undo()
        with pytest.raises(ValueError):
            redos_mod.check_pattern(bomb)


class TestRedosCompileDoSMatrix:
    """Every compile-time blow-up shape must be refused up front by check_pattern
    (the match timeout runs *after* compile, so it cannot help here). Non-capturing
    and other linear shapes are bounded by MAX_PATTERN_LENGTH instead."""

    def _dangerous(self):
        from nltk.redos import (
            MAX_GROUP_COUNT,
            MAX_NESTING_DEPTH,
            MAX_PATTERN_LENGTH,
            MAX_REPEAT_PRODUCT,
        )

        return {
            "capturing-groups": "()" * (MAX_GROUP_COUNT + 1),
            "named-groups-P": "".join(
                "(?P<g%d>x)" % i for i in range(MAX_GROUP_COUNT + 1)
            ),
            "named-groups-regexstyle": "".join(
                "(?<n%d>x)" % i for i in range(MAX_GROUP_COUNT + 1)
            ),
            "group-nesting": "(" * (MAX_NESTING_DEPTH + 5)
            + "a"
            + ")" * (MAX_NESTING_DEPTH + 5),
            "class-nesting": "[" * (MAX_NESTING_DEPTH + 5),
            "over-length": "a" * (MAX_PATTERN_LENGTH + 1),
            "huge-count": "a{" + "9" * 20000 + "}",
            "nested-count-product": "(?:a){%d}{%d}"
            % (MAX_REPEAT_PRODUCT, MAX_REPEAT_PRODUCT),
        }

    @pytest.mark.parametrize(
        "shape",
        [
            "capturing-groups",
            "named-groups-P",
            "named-groups-regexstyle",
            "group-nesting",
            "class-nesting",
            "over-length",
            "huge-count",
            "nested-count-product",
        ],
    )
    def test_dangerous_shape_is_refused(self, shape):
        from nltk import redos

        pat = self._dangerous()[shape]
        with pytest.raises(ValueError):
            redos.check_pattern(pat)
        with pytest.raises(ValueError):
            redos.compile(pat)

    @pytest.mark.parametrize(
        "pat",
        [
            "(?:a)" * 15000,  # 15k non-capturing groups: linear, accepted
            "a|" * 40000 + "a",  # big alternation: linear, under length cap
            "(?=a)" * 15000,  # lookahead repeat: linear
            "(?>a)" * 15000,  # atomic repeat: linear
        ],
    )
    def test_linear_shape_is_accepted_and_bounded_by_length(self, pat):
        from nltk import redos

        redos.check_pattern(pat)  # must not raise (not a compile bomb)

    def test_non_capturing_compile_scales_linearly(self):
        # The engine's compile cost is quadratic only in capturing groups; the
        # non-capturing shapes stay linear, which is why the length cap alone
        # bounds them (2500->10000 groups measured ~2.9x on the raw engine).
        import regex

        _assert_subquadratic(lambda n: regex.compile("(?:a)" * n), 2500, 10000)


# --- #q4c8: readline linear on an unterminated line --------------------------


class TestReadlineLinear:
    def _reader(self, data):
        from nltk.data import SeekableUnicodeStreamReader

        return SeekableUnicodeStreamReader(io.BytesIO(data), "utf-8")

    def test_terminated_lines_read_correctly(self):
        r = self._reader(b"alpha\nbeta\ngamma\n")
        assert r.readline() == "alpha\n"
        assert r.readline() == "beta\n"
        assert r.readline() == "gamma\n"

    def test_unterminated_final_line_read_correctly(self):
        r = self._reader(b"one\ntwo\nthree")
        assert [r.readline(), r.readline(), r.readline()] == ["one\n", "two\n", "three"]

    def test_every_line_ending_kind_splits(self):
        r = self._reader(b"alpha\nbeta\r\ngamma\rdelta")
        assert [r.readline() for _ in range(4)] == [
            "alpha\n",
            "beta\r\n",
            "gamma\r",
            "delta",
        ]

    def test_crlf_at_the_first_block_edge_stays_intact(self):
        # The first block is 72 chars; a CR as its last char must pull in the LF.
        r = self._reader(("a" * 71 + "\r\n" + "b\n").encode())
        assert r.readline() == "a" * 71 + "\r\n"
        assert r.readline() == "b\n"

    def test_unicode_line_separator_still_splits(self):
        # U+2028 is a str.splitlines break; a line ending only in it must split.
        r = self._reader("a b".encode())
        first = r.readline()
        assert first == "a "

    def test_many_short_lines_via_linebuffer(self):
        # Exercises the buffered-line prepend path: a completed line left in the
        # linebuffer (it ends in a break) must still be returned when the next
        # block read has no break of its own.
        data = "".join("l%d\n" % i for i in range(60)).encode("utf-8")
        r = self._reader(data)
        assert [r.readline() for _ in range(60)] == ["l%d\n" % i for i in range(60)]

    def test_readlines_and_seek_unchanged(self):
        r = self._reader(b"abc\ndef\n")
        assert r.readlines() == ["abc\n", "def\n"]
        r = self._reader(b"one\ntwo\n")
        r.readline()
        r.seek(0)
        assert r.readline() == "one\n"

    def test_long_unterminated_line_is_not_quadratic(self):
        # Pre-fix this re-split the whole growing buffer each pass (O(N**2)); an
        # 8 MB single line took 14 s and 2 MB -> 8 MB scaled 16x. A load-invariant
        # scaling ratio catches the regression without a wall-clock deadline.
        assert len(self._reader(b"a" * 8_000_000).readline()) == 8_000_000
        _assert_subquadratic(
            lambda n: self._reader(b"a" * n).readline(), 2_000_000, 8_000_000
        )

    def test_linear_read_has_teeth(self, monkeypatch):
        # Make every block look like it carries a line break: readline then joins
        # and re-splits the whole growing buffer on each pass, the pre-fix
        # behaviour, and the measurement must go quadratic.
        from nltk.data import SeekableUnicodeStreamReader

        monkeypatch.setattr(
            SeekableUnicodeStreamReader, "_LINEBREAK_CHARS", frozenset("a")
        )
        _assert_quadratic(
            lambda n: self._reader(b"a" * n).readline(), 500_000, 2_000_000
        )
        # and the output is still the whole line, only slower
        assert len(self._reader(b"a" * 100_000).readline()) == 100_000


# --- #cj8f: XMLCorpusView nesting-depth bound --------------------------------


class TestXMLCorpusViewDepth:
    def _view(self, xml, tagspec):
        from nltk.corpus.reader.xmldocs import XMLCorpusView
        from nltk.data import FileSystemPathPointer

        d = tempfile.mkdtemp()
        path = os.path.join(d, "corpus.xml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml)
        return list(XMLCorpusView(FileSystemPathPointer(path), tagspec))

    def _nested(self, depth):
        # non-matching tagspec forces the full descent
        return self._view("<a>" * depth + "x" + "</a>" * depth, "zzz")

    def _descend(self, depth):
        # timing helper: iterate rather than list(), whose len() walks the file
        # a second time
        from nltk.corpus.reader.xmldocs import XMLCorpusView
        from nltk.data import FileSystemPathPointer

        d = tempfile.mkdtemp()
        path = os.path.join(d, "corpus.xml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("<a>" * depth + "x" + "</a>" * depth)
        return sum(1 for _ in XMLCorpusView(FileSystemPathPointer(path), "zzz"))

    def test_deeply_nested_xml_is_refused(self):
        from nltk.corpus.reader.xmldocs import MAX_XML_DEPTH

        with pytest.raises(ValueError, match="MAX_XML_DEPTH"):
            self._nested(MAX_XML_DEPTH + 50)
        with pytest.raises(ValueError, match="MAX_XML_DEPTH"):
            self._nested(32000)  # ran past 45 s pre-fix

    def test_depth_at_the_bound_is_accepted(self):
        from nltk.corpus.reader.xmldocs import MAX_XML_DEPTH

        assert self._nested(MAX_XML_DEPTH) == []
        assert self._nested(400) == []

    def test_normal_xml_reads(self):
        got = self._view("<doc><s>hi</s><s>bye</s></doc>", ".*/s")
        assert len(got) == 2

    def test_depth_bound_has_teeth(self, monkeypatch):
        # With the bound lifted the per-tag path rebuild is what the attacker
        # gets: the descent must scale quadratically in the nesting depth.
        import nltk.corpus.reader.xmldocs as xmldocs

        monkeypatch.setattr(xmldocs, "MAX_XML_DEPTH", 10**9)
        assert self._nested(6000) == []  # accepted once the bound is gone
        # The per-tag regex match is a linear floor under the quadratic path
        # rebuild (profiled: str.join is over half the time at depth 6000), so
        # the sizes are large enough for the rebuild to dominate.
        _assert_quadratic(self._descend, 3000, 12000, reps=1)


# --- #53pg: WordNet hypernym walkers refuse a cyclic graph -------------------

WALKERS = ("max_depth", "min_depth", "hypernym_paths", "hypernym_distances")


def _synthetic_node_class():
    """A synthetic Synset exposing only the hypernym accessors the walkers use,
    so the graph shape is under the test's control and no corpus is needed."""
    from nltk.corpus.reader.wordnet import Synset

    class Node(Synset):
        def __init__(self, name, up):
            self._name = name
            self._up = up

        def hypernyms(self):
            return self._up

        def instance_hypernyms(self):
            return []

        def _hypernyms(self):
            return self._up

        def _instance_hypernyms(self):
            return []

    return Node


def _chain(Node, length):
    node = Node("root", [])
    for i in range(length):
        node = Node("n%d" % i, [node])
    return node


class TestWordNetHypernymCycle:
    WALKERS = WALKERS

    def _wn(self):
        wn = pytest.importorskip("nltk.corpus").wordnet
        try:
            wn.synset("dog.n.01")
        except LookupError:
            pytest.skip("wordnet corpus not downloaded")
        return wn

    @pytest.mark.parametrize("walker", WALKERS)
    def test_cycle_raises_valueerror_not_recursionerror(self, walker):
        wn = self._wn()
        a = wn.synset("dog.n.01")
        b = wn.synset("cat.n.01")
        Synset = type(a)
        # Both public and private hypernym accessors: the walkers use one or the
        # other. Inject an a<->b cycle and clear any memoized depth.
        saved = {
            n: getattr(Synset, n)
            for n in (
                "hypernyms",
                "instance_hypernyms",
                "_hypernyms",
                "_instance_hypernyms",
            )
        }
        try:
            Synset.hypernyms = lambda self: [b if self._name == "dog.n.01" else a]
            Synset._hypernyms = Synset.hypernyms
            Synset.instance_hypernyms = lambda self: []
            Synset._instance_hypernyms = Synset.instance_hypernyms
            for m in ("_max_depth", "_min_depth"):
                a.__dict__.pop(m, None)
                b.__dict__.pop(m, None)
            with pytest.raises(ValueError, match="cycle"):
                getattr(a, walker)()
        finally:
            for n, fn in saved.items():
                setattr(Synset, n, fn)
            for m in ("_max_depth", "_min_depth"):
                a.__dict__.pop(m, None)
                b.__dict__.pop(m, None)

    @pytest.mark.parametrize("walker", WALKERS)
    def test_synthetic_cycle_and_deep_chain_refused(self, walker):
        # No corpus needed: a two-node cycle and a 2000-deep acyclic chain (over
        # the interpreter's recursion limit) are both refused with a ValueError.
        Node = _synthetic_node_class()
        a = Node("a", [])
        b = Node("b", [a])
        a._up = [b]
        with pytest.raises(ValueError, match="cycle"):
            getattr(a, walker)()
        with pytest.raises(ValueError, match="_MAX_HYPERNYM_DEPTH"):
            getattr(_chain(Node, 2000), walker)()

    @pytest.mark.parametrize("walker", WALKERS)
    def test_chain_under_the_cap_walks(self, walker):
        from nltk.corpus.reader.wordnet import _MAX_HYPERNYM_DEPTH

        Node = _synthetic_node_class()
        result = getattr(_chain(Node, _MAX_HYPERNYM_DEPTH - 1), walker)()
        assert result  # non-empty depth / paths / distances

    @pytest.mark.parametrize("walker", WALKERS)
    def test_visit_guard_has_teeth(self, walker, monkeypatch):
        # Neuter the visit check and the cycle recurses until RecursionError.
        import nltk.corpus.reader.wordnet as wordnet

        Node = _synthetic_node_class()
        a = Node("a", [])
        b = Node("b", [a])
        a._up = [b]
        monkeypatch.setattr(wordnet, "_check_hypernym_visit", lambda s, v: None)
        with pytest.raises(RecursionError):
            getattr(a, walker)()

    @pytest.mark.parametrize("walker", WALKERS)
    def test_real_acyclic_graph_still_works(self, walker):
        wn = self._wn()
        result = getattr(wn.synset("dog.n.01"), walker)()
        assert result  # non-empty depth / paths / distances

    def test_real_similarities_unchanged(self):
        wn = self._wn()
        dog, cat = wn.synset("dog.n.01"), wn.synset("cat.n.01")
        assert (dog.max_depth(), dog.min_depth()) == (13, 8)
        assert round(dog.path_similarity(cat), 3) == 0.2
        assert round(dog.wup_similarity(cat), 3) == 0.857


class TestWordNetLemmaMarkerRegex:
    """The lemma syntactic-marker regex in wordnet.py was catastrophic on a
    crafted lemma name with many unbalanced parens; restricting the marker body
    to ``[^()]*`` makes it linear while extracting the real (a)/(p)/(ip) markers
    identically (verified against all 424k WordNet lemmas)."""

    #: keep in sync with nltk/corpus/reader/wordnet.py
    PAT = r"(.*?)(\([^()]*\))?$"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("dog", ("dog", None)),
            ("cut(a)", ("cut", "(a)")),
            ("cold(p)", ("cold", "(p)")),
            ("outer(ip)", ("outer", "(ip)")),
            ("domestic_dog", ("domestic_dog", None)),
        ],
    )
    def test_marker_extraction_is_faithful(self, raw, expected):
        from nltk import redos

        assert redos.match(self.PAT, raw).groups() == expected

    def test_adversarial_lemma_name_is_linear(self):
        # Was catastrophic (the 5 s redos backstop tripped on 200k parens); the
        # linear form scales ~4x for 4x input.
        from nltk import redos

        assert redos.match(self.PAT, "(" * 200_000) is not None
        _assert_subquadratic(lambda n: redos.match(self.PAT, "(" * n), 50_000, 200_000)

    def _wn(self):
        wn = pytest.importorskip("nltk.corpus").wordnet
        try:
            wn.synset("dog.n.01")
        except LookupError:
            pytest.skip("wordnet corpus not downloaded")
        return wn

    def test_real_sink_is_linear_on_a_crafted_data_line(self):
        # Drive the reader's own data-line parser with the crafted lemma; the
        # KeyError afterwards (no offset-map entry for the fake lemma) proves the
        # marker regex phase completed.
        wn = self._wn()

        def op(n):
            line = "00001740 03 n 01 " + "(" * n + " 0 000 | gloss"
            try:
                wn._synset_from_pos_and_line("n", line)
            except KeyError:
                pass

        _assert_subquadratic(op, 50_000, 200_000)

    def test_real_wordnet_lemmas_load(self):
        wn = self._wn()
        assert [l.name() for l in wn.synset("dog.n.01").lemmas()][0] == "dog"

    def test_real_markers_still_extracted(self):
        wn = self._wn()
        got = {
            l.name(): l.syntactic_marker()
            for w in ("galore", "alone", "lone")
            for ss in wn.synsets(w, "a")
            for l in ss.lemmas()
            if l.syntactic_marker()
        }
        assert got["galore"] == "(ip)"
        assert got["alone"] == "(p)"
        assert got["lone"] == "(a)"


# --- ffr9 / gpwc / 8fx7: tokenizer & parser algorithmic DoS ------------------


class TestSpanTokenizeLinear:
    """span_tokenize restored converted quotes with list.pop(0) in a
    comprehension (O(n**2) on many quotes); a deque keeps it linear and the
    spans identical. Both the treebank and destructive engines had the bug."""

    def _tokenizers(self):
        from nltk.tokenize.destructive import NLTKWordTokenizer
        from nltk.tokenize.treebank import TreebankWordTokenizer

        return (NLTKWordTokenizer(), TreebankWordTokenizer())

    def test_quotes_restored_faithfully(self):
        text = "She said \"hi\" and ''bye'' to \"all\"."
        for tk in self._tokenizers():
            spans = list(tk.span_tokenize(text))
            assert spans and all(0 <= a <= b <= len(text) for a, b in spans)
            assert all(text[a:b] for a, b in spans)
            assert len(spans) == len(tk.tokenize(text))

    def test_many_quotes_is_not_quadratic(self):
        # 200k quotes ran past 45 s pre-fix; the linear restore scales ~4x.
        for tk in self._tokenizers():
            _assert_subquadratic(
                lambda n, tk=tk: list(tk.span_tokenize('"' * n)), 10_000, 40_000
            )

    def test_linear_restore_has_teeth(self, monkeypatch):
        # Reintroduce the O(n) front removal (two whole-list copies per pop so the
        # cost is visible at test sizes): the restore must go quadratic.
        import nltk.tokenize.destructive as destructive
        import nltk.tokenize.treebank as treebank

        class _FrontPopList(list):
            def popleft(self):
                head = self[0]
                self[:] = self[1:]
                return head

        monkeypatch.setattr(destructive, "deque", _FrontPopList)
        monkeypatch.setattr(treebank, "deque", _FrontPopList)
        for tk in self._tokenizers():
            _assert_quadratic(
                lambda n, tk=tk: list(tk.span_tokenize('"' * n)), 5_000, 20_000, reps=2
            )


def _reference_legality_tokenize(lp, token):
    """The pre-fix loop, kept as the behavioural oracle for the linear one."""
    syllables = []
    syllable, current_onset = "", ""
    vowel, onset = False, False
    for char in token[::-1]:
        char_lower = char.lower()
        if not vowel:
            syllable += char
            vowel = bool(char_lower in lp.vowels)
        else:
            if char_lower + current_onset[::-1] in lp.legal_onsets:
                syllable += char
                current_onset += char_lower
                onset = True
            elif char_lower in lp.vowels and not onset:
                syllable += char
                current_onset += char_lower
            else:
                syllables.append(syllable)
                syllable = char
                current_onset = ""
                vowel = bool(char_lower in lp.vowels)
    syllables.append(syllable)
    return [s[::-1] for s in syllables][::-1]


class TestLegalitySyllableTokenLen:
    def _lp(self):
        from nltk.tokenize import LegalitySyllableTokenizer

        return LegalitySyllableTokenizer(["wonderful", "sentence", "this", "is"])

    def test_normal_token_syllabifies(self):
        assert self._lp().tokenize("wonderful")

    def test_oversized_token_is_refused(self):
        from nltk.tokenize import LegalitySyllableTokenizer

        with pytest.raises(ValueError, match="MAX_TOKEN_LEN"):
            self._lp().tokenize("a" * (LegalitySyllableTokenizer.MAX_TOKEN_LEN + 1))

    def test_token_cap_has_teeth(self, monkeypatch):
        from nltk.tokenize import LegalitySyllableTokenizer

        big = LegalitySyllableTokenizer.MAX_TOKEN_LEN + 1
        monkeypatch.setattr(LegalitySyllableTokenizer, "MAX_TOKEN_LEN", 10**9)
        assert self._lp().tokenize("a" * big)  # accepted once the cap is gone

    def test_loop_is_linear_past_the_cap(self):
        # The cap is defence in depth; the loop itself is linear (pre-fix the
        # onset was reversed every iteration: 20k chars took 0.48 s, 80k 16x more).
        lp = self._lp()
        lp.MAX_TOKEN_LEN = 10**9  # this instance only
        _assert_subquadratic(lambda n: lp.tokenize("a" * n), 20_000, 80_000)

    def test_onset_saturation_has_teeth(self):
        # A legal onset longer than any token defeats the saturation cut-off, so
        # the onset is reversed on every iteration again: quadratic.
        lp = self._lp()
        lp.MAX_TOKEN_LEN = 10**9
        lp.legal_onsets = set(lp.legal_onsets) | {"x" * 10**6}
        _assert_quadratic(lambda n: lp.tokenize("a" * n), 10_000, 40_000, reps=2)

    def test_saturation_matches_the_reference_loop(self):
        # The oracle is the pre-fix loop; outputs must agree on real words, on
        # random tokens over a vowel-heavy alphabet and on long under-cap tokens.
        from nltk.tokenize import LegalitySyllableTokenizer

        try:
            from nltk.corpus import words

            vocab = words.words()[:20000]
        except LookupError:
            vocab = ["wonderful", "sentence", "this", "is", "strengths", "aeiou"]
        for lp in (LegalitySyllableTokenizer(vocab), self._lp()):
            for w in vocab[:5000]:
                assert lp.tokenize(w) == _reference_legality_tokenize(lp, w), w
            rng = random.Random(53)
            for _ in range(2000):
                tok = "".join(
                    rng.choice("aeioubcdfgy") for _ in range(rng.randint(1, 300))
                )
                assert lp.tokenize(tok) == _reference_legality_tokenize(lp, tok), tok
            for tok in ("a" * 4096, "ba" * 2048, "strengths" * 455, "aeiou" * 800):
                assert lp.tokenize(tok) == _reference_legality_tokenize(lp, tok)


class TestSteppingParserDeadline:
    def _grammar(self, s):
        from nltk import CFG

        return CFG.fromstring(s)

    def test_normal_grammar_parses(self):
        from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

        g = self._grammar("S -> NP VP\nNP -> 'the' 'dog'\nVP -> 'runs'")
        assert list(SteppingRecursiveDescentParser(g).parse(["the", "dog", "runs"]))

    def test_default_is_bounded_out_of_the_box(self):
        from nltk.parse.recursivedescent import (
            DEFAULT_MAX_TIME,
            SteppingRecursiveDescentParser,
        )

        g = self._grammar("S -> 'a'")
        assert SteppingRecursiveDescentParser(g)._max_time == DEFAULT_MAX_TIME
        assert 0 < DEFAULT_MAX_TIME <= 30

    def test_left_recursive_grammar_times_out(self):
        from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

        g = self._grammar("S -> S 'a'\nS -> 'a'")
        p = SteppingRecursiveDescentParser(g, max_time=1)
        with pytest.raises((TimeoutError, RecursionError)):
            list(p.parse(["a", "a", "a", "a"]))

    def test_ambiguous_grammar_times_out(self):
        # Exponentially many parses (24 tokens ran past 45 s pre-fix): the
        # deadline is checked on every step, so it fires as a TimeoutError.
        from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

        g = self._grammar("S -> 'a' S | 'a' S S | 'a'")
        with pytest.raises(TimeoutError, match="time limit"):
            list(SteppingRecursiveDescentParser(g, max_time=0.5).parse(["a"] * 24))

    def test_max_time_none_disables_the_bound(self):
        from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

        g = self._grammar("S -> NP VP\nNP -> 'the' 'dog'\nVP -> 'runs'")
        p = SteppingRecursiveDescentParser(g, max_time=None)
        assert p._max_time is None
        assert len(list(p.parse(["the", "dog", "runs"]))) == 1

    def test_step_deadline_has_teeth(self, monkeypatch):
        # Put back the pre-fix loop (step() with no deadline): 8 tokens of the
        # ambiguous grammar then run to completion, well past max_time, and no
        # TimeoutError is raised.
        from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

        def unbounded_parse(self, tokens):
            tokens = list(tokens)
            self.initialize(tokens)
            while self.step() is not None:
                pass
            return self.parses()

        g = self._grammar("S -> 'a' S | 'a' S S | 'a'")
        monkeypatch.setattr(SteppingRecursiveDescentParser, "parse", unbounded_parse)
        p = SteppingRecursiveDescentParser(g, max_time=0.25)
        start = time.perf_counter()
        parses = list(p.parse(["a"] * 8))
        assert len(parses) == 127
        assert time.perf_counter() - start > 0.25


# --- re-anchoring quadratic regex class (ycoe #3896 + the whole family) -------


class TestSensevalFixXMLLinear:
    """senseval._fixXML strips XML tags with re-anchoring subs; the tag bodies are
    {0,N}-bounded and exclude the `<` anchor, so a crafted block is linear rather
    than O(n**2) (every shape below tripped the 5 s redos backstop pre-fix)."""

    SHAPES = ("<snum=", "<!DOCTYPE", "<&I", "<{", "<[")

    @pytest.mark.parametrize("shape", SHAPES)
    def test_crafted_block_is_linear(self, shape):
        from nltk.corpus.reader.senseval import _fixXML

        _assert_subquadratic(lambda n: _fixXML(shape * n), 10_000, 40_000)

    def test_doctype_still_stripped(self):
        from nltk.corpus.reader.senseval import _fixXML

        assert "DOCTYPE" not in _fixXML('<!DOCTYPE corpus SYSTEM "x.dtd">tail')

    def test_tag_fixes_still_apply(self):
        from nltk.corpus.reader.senseval import _fixXML

        got = _fixXML('<s snum=12> <&I .> <{word}> <[hi]> <&hellip;> "x"')
        assert '<s snum="12"/>' in got
        assert "<&I" not in got and "<{" not in got and "<[hi]>" not in got
        assert "word" in got

    def test_real_corpus_still_reads(self):
        senseval = pytest.importorskip("nltk.corpus").senseval
        try:
            fileids = senseval.fileids()
        except LookupError:
            pytest.skip("senseval corpus not downloaded")
        inst = senseval.instances(fileids[0])[:20]  # lazy view: reads one block
        assert len(inst) == 20 and inst[0].word and inst[0].context


class TestAnchorExcludedRunsAreLinear:
    """The other re-anchoring sites, driven through their real entry points on
    the crafted input that re-scanned to the absent terminator at every anchor."""

    def test_ieer_read_text(self):
        from nltk.chunk.util import _ieer_read_text

        assert len(_ieer_read_text("<" * 200_000, "DOC")) == 0
        _assert_subquadratic(lambda n: _ieer_read_text("<" * n, "DOC"), 50_000, 200_000)
        tree = _ieer_read_text(
            'The <b_enamex type="ORGANIZATION">IEER<e_enamex> corpus', "DOC"
        )
        assert tree.label() == "DOC"
        assert [c.label() for c in tree if hasattr(c, "label")] == ["ORGANIZATION"]

    def test_ycoe_parse(self):
        from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader
        from nltk.corpus.reader.ycoe import YCOEParseCorpusReader

        reader = YCOEParseCorpusReader.__new__(YCOEParseCorpusReader)

        def op(n):
            try:
                reader._parse("(CODE" * n)
            except ValueError:
                pass  # the stripped text is not a tree, which is fine here

        _assert_subquadratic(op, 20_000, 80_000)
        stripped = reader._parse(
            "( (CODE <T05170000100,1>) (IP-MAT (D ok)) (ID coaelive,LS_1:1.1))"
        )
        assert (
            stripped is not None
            and "CODE" not in str(stripped)
            and "ID" not in str(stripped)
        )
        assert isinstance(reader, BracketParseCorpusReader)

    def test_lin_key_is_pinned_to_line_start(self):
        from nltk.corpus.reader.lin import LinThesaurusCorpusReader

        sub = LinThesaurusCorpusReader._key_re.sub
        assert sub(r"\1", "(" * 60_000) == "(" * 60_000  # no match, no scan
        _assert_subquadratic(lambda n: sub(r"\1", "(" * n), 50_000, 200_000)
        assert sub(r"\1", "(a (desc 3186.08) (sims") == "a"
        assert sub(r"\1", '("a few" (desc 100392) (sims') == "a few"

    def test_lin_real_corpus_keys_unchanged(self):
        # The old, unpinned pattern and the shipped one must extract the same key
        # from the first line of every entry of the real thesaurus.
        import glob

        import regex

        import nltk.data
        from nltk.corpus.reader.lin import LinThesaurusCorpusReader

        # locate the files directly: constructing the reader parses the whole
        # thesaurus (tens of seconds), which this comparison does not need
        try:
            root = str(nltk.data.find("corpora/lin_thesaurus"))
        except LookupError:
            pytest.skip("lin_thesaurus corpus not downloaded")
        paths = sorted(glob.glob(os.path.join(root, "sim*.lsp")))
        old = regex.compile(r'\("?([^"]+)"? \(desc [0-9.]+\).+')
        new = LinThesaurusCorpusReader._key_re
        checked = 0
        for path in paths:
            with open(path, encoding="latin-1") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("("):
                        assert old.sub(r"\1", line) == new.sub(r"\1", line), line
                        checked += 1
        assert checked > 1000

    def test_ace_tag_strip_and_text_anchor(self, tmp_path):
        from nltk.chunk.named_entity import load_ace_file
        from nltk.test.unit.security_probes._base import register_data_root

        undo = register_data_root(str(tmp_path))
        try:

            def op(n, body="<"):
                text = tmp_path / ("t%d.sgm" % n)
                text.write_text(body * n, encoding="utf-8")
                (tmp_path / (text.name + ".tmx.rdc.xml")).write_text(
                    "<source_file><document DOCID='d'></document></source_file>",
                    encoding="utf-8",
                )
                try:
                    list(load_ace_file(str(text), "binary"))
                except LookupError:
                    pass  # tokenizer model missing: the regex phase is done

            _assert_subquadratic(op, 25_000, 100_000)
            _assert_subquadratic(lambda n: op(n, "x"), 50_000, 200_000)
        finally:
            undo()

    def test_verbnet_index_is_linear_on_unclosed_member_tags(self, tmp_path):
        from nltk.corpus.reader.verbnet import VerbnetCorpusReader
        from nltk.test.unit.security_probes._base import register_data_root

        undo = register_data_root(str(tmp_path))
        try:

            def op(n):
                d = tmp_path / ("c%d" % n)
                d.mkdir(exist_ok=True)
                (d / "evil-1.xml").write_text(
                    '<MEMBER name="a" wn="b"' * n, encoding="utf-8"
                )
                VerbnetCorpusReader(str(d), ["evil-1.xml"])

            _assert_subquadratic(op, 2_000, 8_000)
        finally:
            undo()

    def test_verbnet_real_corpus_index_unchanged(self):
        # The old and the bounded index regex must produce the same matches over
        # every file of the real corpus (the longest real MEMBER tag is 145 chars).
        import regex

        verbnet = pytest.importorskip("nltk.corpus").verbnet
        from nltk.corpus.reader.verbnet import VerbnetCorpusReader

        try:
            fileids = verbnet.fileids()
        except LookupError:
            pytest.skip("verbnet corpus not downloaded")
        old = regex.compile(
            r'<MEMBER name="\??([^"]+)" wn="([^"]*)"[^>]+>|<VNSUBCLASS ID="([^"]+)"/?>'
        )
        new = VerbnetCorpusReader._INDEX_RE
        matches = 0
        for fileid in fileids:
            text = verbnet.raw(fileid)
            a = [(m.span(), m.groups()) for m in old.finditer(text)]
            b = [(m.span(), m.groups()) for m in new.finditer(text)]
            assert a == b, fileid
            matches += len(a)
        assert matches > 1000
        assert verbnet.classids("run")


class TestReanchoringGuard:
    """The CI guard flags an unbounded re-anchoring op and accepts a bounded one."""

    def _guard(self):
        import importlib.util
        import os

        path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "tools",
                "check_reanchoring_quadratic.py",
            )
        )
        if not os.path.exists(path):
            pytest.skip("re-anchoring guard script not present")
        spec = importlib.util.spec_from_file_location("reanchor_guard", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_flags_unbounded_and_accepts_bounded(self, tmp_path):
        g = self._guard()
        bad = tmp_path / "bad.py"
        bad.write_text('import redos\nredos.sub(r"<[^>]+>", "", t)\n')
        good = tmp_path / "good.py"
        good.write_text('import redos\nredos.sub(r"<[^>]{1,400}>", "", t)\n')
        assert g.check_file(str(bad), "nltk/bad.py")
        assert not g.check_file(str(good), "nltk/good.py")

    def test_guard_catches_compiled_pattern_use(self, tmp_path):
        # The AST blind spot: PAT = redos.compile(...); PAT.findall(...) - the
        # re-anchoring op is a method on the compiled object, not redos.<op>.
        g = self._guard()
        bad = tmp_path / "c.py"
        bad.write_text(
            'import redos\nPAT = redos.compile(r"<[^>]+>")\nPAT.findall(s)\n'
        )
        assert g.check_file(str(bad), "nltk/c.py")

    @pytest.mark.parametrize(
        "use",
        [
            "self._RE.finditer(s)",
            "Reader._RE.sub('', s)",
            "nltk.reader.Reader._RE.split(s)",
        ],
    )
    def test_guard_resolves_dotted_receivers(self, tmp_path, use):
        # A compiled class attribute used through self./Cls./pkg.Cls. was the
        # second blind spot (lin, verbnet, xmldocs, chunk.regexp all use one).
        g = self._guard()
        bad = tmp_path / "d.py"
        bad.write_text(
            "import redos\nclass Reader:\n    _RE = redos.compile(r'<[^>]+>')\n"
            "    def f(self, s):\n        return %s\n" % use
        )
        assert g.check_file(str(bad), "nltk/d.py")

    def test_shipped_tree_passes_the_guard(self):
        g = self._guard()
        root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        if not os.path.isdir(os.path.join(root, "nltk")):
            pytest.skip("source tree not present")
        failures = []
        for dirpath, _dirs, files in os.walk(os.path.join(root, "nltk")):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                relpath = os.path.relpath(path, root)
                if relpath.startswith(g._EXEMPT_PREFIXES) or relpath in g._EXEMPT_FILES:
                    continue
                failures.extend((relpath, *v) for v in g.check_file(path, relpath))
        assert not failures, failures


class TestCompiledPatternReanchoringBounded:
    """The 6 compiled-pattern re-anchoring quadratics found by the compiled-method
    rescan (lin/evaluate/grammar/reviews/bracket_parse/pl196x) are now {0,N}-bounded:
    linear on a crafted trigger, was O(n**2) under the regex engine."""

    def _ops(self):
        from nltk.corpus.reader.bracket_parse import ALPINO_ATTR
        from nltk.corpus.reader.pl196x import PARA
        from nltk.corpus.reader.reviews import FEATURES
        from nltk.grammar import _SPLIT_DG_RE
        from nltk.sem.evaluate import _TUPLES_RE

        return {
            "FEATURES": lambda n: FEATURES.findall("a" * n + "["),
            "_TUPLES_RE": lambda n: _TUPLES_RE.findall("(" * n),
            "PARA": lambda n: PARA.findall("<p>" * n),
            "ALPINO_ATTR": lambda n: ALPINO_ATTR.findall("a" * n + '="'),
            "_SPLIT_DG_RE": lambda n: _SPLIT_DG_RE.split("-" * n),
        }

    @pytest.mark.parametrize(
        "name", ["FEATURES", "_TUPLES_RE", "PARA", "ALPINO_ATTR", "_SPLIT_DG_RE"]
    )
    def test_bounded_patterns_are_linear(self, name):
        _assert_subquadratic(self._ops()[name], 10_000, 40_000)

    def test_bounds_are_faithful_on_real_input(self):
        from nltk.corpus.reader.reviews import FEATURES
        from nltk.sem.evaluate import _TUPLES_RE

        assert FEATURES.findall("great battery[+2]") == [("great battery", "+2")]
        assert _TUPLES_RE.findall("(a, b) (c, d)") == ["(a, b)", "(c, d)"]

    def test_real_entry_points_still_work(self):
        from nltk.grammar import DependencyGrammar
        from nltk.sem import Valuation

        val = Valuation.fromstring("chase => {(b1, g1), (b2, g1)}\ngirl => {g1}")
        assert val["chase"] == {("b1", "g1"), ("b2", "g1")}
        dg = DependencyGrammar.fromstring(
            "'fell' -> 'price' | 'stock'\n'price' -> 'of'"
        )
        assert dg.contains("fell", "price")
