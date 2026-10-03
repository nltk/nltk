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
* ``XMLCorpusView.read_block`` bounds XML nesting depth and the joined path's
  width, and extends the path per tag (the per-tag ``"/".join(context)`` cost
  the path's length, so deep nesting, or long names under a prefix within the
  depth cap, was O(n**2)).
* the pl196x ``PARA``/``SENT``/``WORD``/``TAGGEDWORD`` attribute runs are
  bounded, so an open tag with its ``>`` omitted no longer re-scans the block.
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

import functools
import io
import os
import random
import tempfile
import time

import pytest

from nltk.test.unit import timing
from nltk.test.unit.security_probes.ghsa_53pg_5qp8_mhvr import (
    WALKERS,
    _chain,
    _node_class,
)

QUADRATIC_RATIO = timing.QUADRATIC_RATIO

# Every op here computes, so each side of a ratio is charged its CPU time; the
# measurement itself is the suite's one rule in nltk.test.unit.timing.
_assert_subquadratic = functools.partial(timing.assert_subquadratic, cpu_bound=True)


def _assert_quadratic(op, small, big, reps=3, factor=QUADRATIC_RATIO, noise_floor=0.02):
    """Negative control: with a guard neutered the sink must scale super-linearly.

    The floor is lower than the positive check's: the neutered small side is
    sized to clear 20 ms even on a fast runner, and a floor of 0.1 s would
    hide a real 16x as 5x there.
    """
    ratio = timing.scaling_ratio(
        op, small, big, reps=reps, noise_floor=noise_floor, cpu_bound=True
    )
    assert ratio >= factor, (small, big, ratio)


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

    # Keyed by a short label: pytest puts the parametrized id into the
    # PYTEST_CURRENT_TEST environment variable, and a 100 KB pattern as the
    # id overflows the 32767-character limit Windows puts on one variable.
    LINEAR_SHAPES = {
        "non-capturing-15k": lambda: "(?:a)" * 15000,  # linear, accepted
        "alternation-40k": lambda: "a|" * 40000 + "a",  # linear, under length cap
        "lookahead-15k": lambda: "(?=a)" * 15000,  # linear
        "atomic-15k": lambda: "(?>a)" * 15000,  # linear
    }

    @pytest.mark.parametrize("shape", sorted(LINEAR_SHAPES))
    def test_linear_shape_is_accepted_and_bounded_by_length(self, shape):
        from nltk import redos

        pat = self.LINEAR_SHAPES[shape]()
        redos.check_pattern(pat)  # must not raise (not a compile bomb)

    def test_non_capturing_compile_scales_linearly(self):
        # The engine's compile cost is quadratic only in capturing groups; the
        # non-capturing shapes stay linear, which is why the length cap alone
        # bounds them (2500->10000 groups measured ~2.9x on the raw engine).
        import regex

        _assert_subquadratic(lambda n: regex.compile("(?:a)" * n), 2500, 10000)


# --- #cj8f: XMLCorpusView nesting-depth bound --------------------------------


class TestXMLCorpusViewDepth:
    def _view(self, xml, tagspec):
        # The corpus file must live inside a registered data root: on Linux
        # mkdtemp() lands in /tmp, which pathsec does not trust (on macOS the
        # private temp dir is a root, which hides the difference).
        import shutil

        from nltk.corpus.reader.xmldocs import XMLCorpusView
        from nltk.data import FileSystemPathPointer
        from nltk.test.unit.security_probes._base import register_data_root

        d = tempfile.mkdtemp()
        undo = register_data_root(d)
        try:
            path = os.path.join(d, "corpus.xml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(xml)
            return list(XMLCorpusView(FileSystemPathPointer(path), tagspec))
        finally:
            undo()
            shutil.rmtree(d, ignore_errors=True)

    def _nested(self, depth):
        # non-matching tagspec forces the full descent
        return self._view("<a>" * depth + "x" + "</a>" * depth, "zzz")

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

    def _rebuild_work(self, depth):
        # Characters of root-to-node path that read_block hands the tagspec
        # over the whole file: the work the per-tag rebuild does, counted
        # rather than timed, so the measure is load- and platform-invariant.
        import shutil

        from nltk.corpus.reader.xmldocs import XMLCorpusView
        from nltk.data import FileSystemPathPointer
        from nltk.test.unit.security_probes._base import register_data_root

        class PathMeter:
            chars = 0

            def match(self, path):
                self.chars += len(path)
                return None

        d = tempfile.mkdtemp()
        undo = register_data_root(d)
        try:
            path = os.path.join(d, "corpus.xml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("<a>" * depth + "x" + "</a>" * depth)
            pointer = FileSystemPathPointer(path)
            meter = PathMeter()
            stream = pointer.open("utf8")
            try:
                XMLCorpusView(pointer, "zzz").read_block(stream, tagspec=meter)
            finally:
                stream.close()
            return meter.chars
        finally:
            undo()
            shutil.rmtree(d, ignore_errors=True)

    def test_depth_bound_has_teeth(self, monkeypatch):
        # With the bound lifted the per-tag path rebuild is what the attacker
        # gets: the path work must scale quadratically in the nesting depth
        # (sum of 2k-1 for k up to d is d**2, so 4x depth is 16x work).
        import nltk.corpus.reader.xmldocs as xmldocs

        monkeypatch.setattr(xmldocs, "MAX_XML_DEPTH", 10**9)
        with pytest.raises(ValueError, match="MAX_XML_PATH_LENGTH"):
            self._nested(6000)  # the width bound still refuses a 12 KB path
        monkeypatch.setattr(xmldocs, "MAX_XML_PATH_LENGTH", 10**9)
        assert self._nested(6000) == []  # accepted once both bounds are gone
        small, big = self._rebuild_work(1000), self._rebuild_work(4000)
        assert small == 1000**2 and big == 4000**2, (small, big)
        assert big / small >= QUADRATIC_RATIO

    def test_path_work_meter_reads_the_real_walk(self):
        # Under the bound the meter sees the same d**2 work, which pins that
        # the negative control above measures read_block and not a stand-in.
        from nltk.corpus.reader.xmldocs import MAX_XML_DEPTH

        depth = MAX_XML_DEPTH // 2
        assert self._rebuild_work(depth) == depth**2

    # --- with #3933: the view's tag walk and nltk.xmlsec's tree bound together ---
    def _shallow_match_deep_subtree(self, depth):
        # the matched element sits at depth 2; its subtree is `depth` deep
        return self._view(
            "<doc><e>" + "<a>" * depth + "x" + "</a>" * depth + "</e></doc>", "doc/e"
        )

    def test_a_subtree_under_both_bounds_parses(self):
        got = self._shallow_match_deep_subtree(300)
        assert len(got) == 1 and got[0].tag == "e"

    def test_a_subtree_between_the_two_bounds_is_refused_by_the_view(self):
        from nltk.corpus.reader.xmldocs import MAX_XML_DEPTH
        from nltk.xmlsec import MAX_DEPTH

        assert MAX_XML_DEPTH < MAX_DEPTH  # the stricter bound applies first
        with pytest.raises(ValueError, match="nesting depth"):
            self._shallow_match_deep_subtree((MAX_XML_DEPTH + MAX_DEPTH) // 2)

    def test_a_subtree_past_both_bounds_is_refused_in_bounded_time(self):
        from nltk.xmlsec import MAX_DEPTH

        with timing.budget(30, cpu_bound=True), pytest.raises(
            ValueError, match="nesting depth"
        ):
            self._shallow_match_deep_subtree(MAX_DEPTH * 20)

    def test_with_the_view_bound_lifted_xmlsec_still_refuses_the_tree(
        self, monkeypatch
    ):
        # defence in depth: were the view's walk bound ever lifted, the element
        # it hands over is still parsed through nltk.xmlsec, which refuses it
        import nltk.corpus.reader.xmldocs as xmldocs
        from nltk.xmlsec import MAX_DEPTH, StructureForbidden

        monkeypatch.setattr(xmldocs, "MAX_XML_DEPTH", 10**9)
        with pytest.raises(StructureForbidden, match="nesting depth"):
            self._shallow_match_deep_subtree(MAX_DEPTH + 10)
        assert len(self._shallow_match_deep_subtree(MAX_DEPTH - 10)) == 1


# --- #53pg: WordNet hypernym walkers refuse a cyclic graph -------------------
# WALKERS, _node_class and _chain are the GHSA-53pg probe's own, imported above.


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
        Node = _node_class()
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

        Node = _node_class()
        result = getattr(_chain(Node, _MAX_HYPERNYM_DEPTH - 1), walker)()
        assert result  # non-empty depth / paths / distances

    @pytest.mark.parametrize("walker", WALKERS)
    def test_visit_guard_has_teeth(self, walker, monkeypatch):
        # Neuter the visit check and the cycle recurses until RecursionError.
        import nltk.corpus.reader.wordnet as wordnet

        Node = _node_class()
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
    comprehension (O(n**2) on many quotes); a forward iterator keeps it linear
    and the spans identical. Both engines had the bug. The spans and the linear
    scaling are pinned in test_attack_tokenize_expanded.py; this pins the teeth."""

    def _tokenizers(self):
        from nltk.tokenize.destructive import NLTKWordTokenizer
        from nltk.tokenize.treebank import TreebankWordTokenizer

        return (NLTKWordTokenizer(), TreebankWordTokenizer())

    def test_linear_restore_has_teeth(self, monkeypatch):
        # Reintroduce the O(n) front removal (two whole-list copies per pop so the
        # cost is visible at test sizes): the restore must go quadratic.
        import nltk.tokenize.destructive as destructive
        import nltk.tokenize.treebank as treebank

        class _FrontPopIterator:
            # the engines draw the matched quotes through iter()/next()
            def __init__(self, items):
                self.items = list(items)

            def __iter__(self):
                return self

            def __next__(self):
                if not self.items:
                    raise StopIteration
                head = self.items[0]
                self.items[:] = self.items[1:]
                return head

        monkeypatch.setattr(destructive, "iter", _FrontPopIterator, raising=False)
        monkeypatch.setattr(treebank, "iter", _FrontPopIterator, raising=False)
        for tk in self._tokenizers():
            # 10k/40k: at 4k the neutered small side sat under the 20 ms floor on a
            # Windows runner (its 16k side was 0.156 s), so the ratio was floor-bound
            # and read 7.8x; at 10k both sides resolve on the 15.6 ms CPU clock.
            _assert_quadratic(
                lambda n, tk=tk: list(tk.span_tokenize('"' * n)), 10_000, 40_000, reps=2
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


# --- pl196x: the attribute runs and bodies of PARA/SENT/WORD/TAGGEDWORD are
# bounded and cannot step over another open tag of their own kind ----------------

#: The pre-fix (develop) patterns, verbatim: the oracle for faithfulness and the
#: teeth. An earlier fix, ``[^>]{0,1024}`` and ``.{0,8192}?``, was O(n*bound) on
#: the unterminated trigger and silently dropped the four paragraphs over 8 KB.
_PL196X_PREFIX = {
    "PARA": r"<p(?: [^>]*){0,1}>(.*?)</p>",
    "SENT": r"<s(?: [^>]*){0,1}>(.*?)</s>",
    "TAGGEDWORD": r"<([wc](?: [^>]*){0,1}>)(.*?)</[wc]>",
    "WORD": r"<[wc](?: [^>]*){0,1}>(.*?)</[wc]>",
}
_PL196X_OPEN = {"PARA": "<p ", "SENT": "<s ", "TAGGEDWORD": "<c ", "WORD": "<w "}
_PL196X_CLOSE = {"PARA": "</p>", "SENT": "</s>", "TAGGEDWORD": "</c>", "WORD": "</w>"}


class TestPl196xAttributeRunBounded:
    """``(?: [^>]*){0,1}`` kept an unbounded attribute scan: with the ``>``
    omitted, every ``<p `` anchor re-scanned to the end of the block, O(n**2)
    under findall (2500 opens took 1.1 s, 5000 hit the 5 s redos backstop), and
    ``TEICorpusView.read_block`` reads a whole file with no ``</text>`` into one
    block. The run is now ``[^<>]{0,1024}`` (the corpus's widest is 337 chars)
    and excludes the ``<`` of the next anchor, so the scan stops there: linear
    with a small constant, and the backstop is no longer what bounds it. The
    lazy body likewise cannot step over the next open tag of its own kind."""

    def _pattern(self, name):
        from nltk.corpus.reader import pl196x

        return getattr(pl196x, name)

    def _old_pattern(self, name):
        from nltk import redos

        return redos.compile(_PL196X_PREFIX[name])

    @pytest.mark.parametrize("name", sorted(_PL196X_OPEN))
    def test_unterminated_attribute_is_linear(self, name):
        pat, tag = self._pattern(name), _PL196X_OPEN[name]
        assert "[^<>]{0,1024}" in pat.pattern
        _assert_subquadratic(lambda n: pat.findall(tag * n), 100_000, 400_000)
        # the required literal present once at the end defeats the engine's
        # literal prefilter; the anchor-excluded run keeps this linear too
        close = _PL196X_CLOSE[name]
        _assert_subquadratic(
            lambda n: pat.findall(tag * n + ">" + close), 100_000, 400_000
        )

    @pytest.mark.parametrize("name", sorted(_PL196X_OPEN))
    def test_unclosed_body_is_linear(self, name):
        pat, tag, close = (
            self._pattern(name),
            _PL196X_OPEN[name][:2] + ">",
            _PL196X_CLOSE[name],
        )
        _assert_subquadratic(lambda n: pat.findall(tag * n), 100_000, 400_000)
        _assert_subquadratic(lambda n: pat.findall(tag * n + close), 100_000, 400_000)

    @pytest.mark.parametrize("name", sorted(_PL196X_OPEN))
    def test_attribute_bound_has_teeth(self, name, monkeypatch):
        # The bounded pattern finishes the trigger well inside the backstop; the
        # verbatim pre-fix pattern runs into a 0.5 s backstop on the same
        # trigger (5000 opens ran past 5 s untimed): the bound is the fix.
        import nltk.redos as redos_mod

        pat, tag = self._pattern(name), _PL196X_OPEN[name]
        assert pat.findall(tag * 5_000) == []
        unbounded = self._old_pattern(name)
        monkeypatch.setattr(redos_mod, "DEFAULT_TIMEOUT", 0.5)
        with pytest.raises(TimeoutError):
            unbounded.findall(tag * 5_000)

    def test_bounded_patterns_match_the_verbatim_old_patterns(self):
        # Attribute runs up to the bound and bodies past the earlier 8 KB cap,
        # nested as the corpus nests them: identical to the pre-fix patterns.
        doc = "".join(
            '<p id="%d" %s><s n="%d"><w ana="A%d" lemma="l">tok%d</w>'
            '<c type="interp">,</c> %s</s></p>'
            % (i, "x" * (i % 1000), i, i, i, "b" * (i % 4096))
            for i in range(0, 1100, 7)
        ) + ("<p>" + "<s><w>y</w></s>" * 700 + "</p>")
        for name in _PL196X_OPEN:
            new, old = self._pattern(name).findall(doc), self._old_pattern(
                name
            ).findall(doc)
            assert new == old and len(new) >= 150, (name, len(new), len(old))
        assert len(self._pattern("PARA").findall(doc)[-1]) == 700 * 15
        # the one difference is the bound itself: a run past it is no match
        wide = "<p " + "x" * 1025 + ">body</p>"
        assert self._old_pattern("PARA").findall(wide) == ["body"]
        assert self._pattern("PARA").findall(wide) == []

    def test_real_corpus_reads_identically_through_the_old_patterns(self, monkeypatch):
        # The reader's view (TEICorpusView, as Pl196xCorpusReader.words and
        # tagged_words build it) on a real corpus file, with the shipped
        # patterns and with the verbatim pre-fix ones: identical output.
        import nltk.data
        from nltk.corpus.reader import pl196x
        from nltk.corpus.reader.pl196x import Pl196xCorpusReader, TEICorpusView

        try:
            path = nltk.data.find("corpora/pl196x/a-publi.xml")
        except LookupError:
            pytest.skip("pl196x corpus not downloaded")
        head_len = Pl196xCorpusReader.head_len

        def read():
            return [
                list(TEICorpusView(path, tagged, True, True, head_len=head_len))
                for tagged in (False, True)
            ]

        shipped = read()
        for name in _PL196X_OPEN:
            monkeypatch.setattr(pl196x, name, self._old_pattern(name))
        assert read() == shipped
        words, tagged = shipped
        assert len(words) > 1000 and tagged[0][0][0][1]  # paras of sents of (w, tag)


# --- #cj8f, the path width: XMLCorpusView refuses a wide root-to-node path -----

from nltk import redos  # noqa: E402
from nltk.corpus.reader.xmldocs import MAX_XML_DEPTH  # noqa: E402
from nltk.corpus.reader.xmldocs import XMLCorpusView, safe_fromstring  # noqa: E402
from nltk.data import SeekableUnicodeStreamReader  # noqa: E402
from nltk.termsec import safe_print  # noqa: E402


class _PreFixXMLCorpusView(XMLCorpusView):
    """``read_block`` exactly as shipped at 6b83f4a06 (the depth bound only, the
    path re-joined at every tag): the oracle the width bound's teeth are measured
    against, and the reference the incremental path must reproduce."""

    def read_block(self, stream, tagspec=None, elt_handler=None):
        """
        Read from ``stream`` until we find at least one element that
        matches ``tagspec``, and return the result of applying
        ``elt_handler`` to each element found.
        """
        if tagspec is None:
            tagspec = self._tagspec
        if isinstance(tagspec, str):
            tagspec = redos.compile(tagspec)  # caller-passed raw tagspec: bound both
        if elt_handler is None:
            elt_handler = self.handle_elt

        # Use a stack of strings to keep track of our context:
        context = list(self._tag_context.get(stream.tell()))
        assert context is not None  # check this -- could it ever happen?

        elts = []

        elt_start = None  # where does the elt start
        elt_depth = None  # what context depth
        elt_text = ""

        while elts == [] or elt_start is not None:
            if isinstance(stream, SeekableUnicodeStreamReader):
                startpos = stream.tell()
            xml_fragment = self._read_xml_fragment(stream)

            # End of file.
            if not xml_fragment:
                if elt_start is None:
                    break
                else:
                    raise ValueError("Unexpected end of file")

            # Process each <tag> in the xml fragment.
            for piece in self._XML_PIECE.finditer(xml_fragment):
                if self._DEBUG:
                    safe_print(
                        "{:>25} {}".format("/".join(context)[-20:], piece.group())
                    )

                if piece.group("START_TAG"):
                    name = self._XML_TAG_NAME.match(piece.group()).group(1)
                    # Keep context up-to-date.
                    context.append(name)
                    if len(context) > MAX_XML_DEPTH:
                        raise ValueError(
                            f"XML nesting depth exceeds MAX_XML_DEPTH "
                            f"({MAX_XML_DEPTH}); the input may be adversarially deep."
                        )
                    # Is this one of the elts we're looking for?
                    if elt_start is None:
                        if tagspec.match("/".join(context)):
                            elt_start = piece.start()
                            elt_depth = len(context)

                elif piece.group("END_TAG"):
                    name = self._XML_TAG_NAME.match(piece.group()).group(1)
                    # sanity checks:
                    if not context:
                        raise ValueError("Unmatched tag </%s>" % name)
                    if name != context[-1]:
                        raise ValueError(f"Unmatched tag <{context[-1]}>...</{name}>")
                    # Is this the end of an element?
                    if elt_start is not None and elt_depth == len(context):
                        elt_text += xml_fragment[elt_start : piece.end()]
                        elts.append((elt_text, "/".join(context)))
                        elt_start = elt_depth = None
                        elt_text = ""
                    # Keep context up-to-date
                    context.pop()

                elif piece.group("EMPTY_ELT_TAG"):
                    name = self._XML_TAG_NAME.match(piece.group()).group(1)
                    if elt_start is None:
                        if tagspec.match("/".join(context) + "/" + name):
                            elts.append((piece.group(), "/".join(context) + "/" + name))

            if elt_start is not None:
                # If we haven't found any elements yet, then keep
                # looping until we do.
                if elts == []:
                    elt_text += xml_fragment[elt_start:]
                    elt_start = 0

                # If we've found at least one element, then try
                # backtracking to the start of the element that we're
                # inside of.
                else:
                    # take back the last start-tag, and return what
                    # we've gotten so far (elts is non-empty).
                    if self._DEBUG:
                        safe_print(" " * 36 + "(backtrack)")
                    if isinstance(stream, SeekableUnicodeStreamReader):
                        stream.seek(startpos)
                        stream.char_seek_forward(elt_start)
                    else:
                        stream.seek(-(len(xml_fragment) - elt_start), 1)
                    context = context[: elt_depth - 1]
                    elt_start = elt_depth = None
                    elt_text = ""

        # Update the _tag_context dict.
        pos = stream.tell()
        if pos in self._tag_context:
            assert tuple(context) == self._tag_context[pos]
        else:
            self._tag_context[pos] = tuple(context)

        return [
            elt_handler(
                safe_fromstring(elt.encode("ascii", "xmlcharrefreplace")),
                context,
            )
            for (elt, context) in elts
        ]


class _PathRecorder:
    """A tagspec that never matches and records every path it is handed."""

    def __init__(self):
        self.paths = []

    def match(self, path):
        self.paths.append(path)
        return None


def _wide_xml(depth, name_len, siblings, kind="empty", sib_name="x"):
    name = "n" * name_len
    pre = "".join(f"<{name}{i}>" for i in range(depth))
    post = "".join(f"</{name}{i}>" for i in reversed(range(depth)))
    if kind == "empty":
        mid = f"<{sib_name}/>" * siblings
    else:
        mid = f"<{sib_name}></{sib_name}>" * siblings
    return pre + mid + post


class TestXMLCorpusViewPathWidth:
    """The depth bound left the per-tag path cost unbounded in width: 400 levels
    of 1000-char names (under the cap) made every one of many siblings cost a
    400 KB path, O(filesize**2) (a 962 KB file took 9.9 s). The joined path is
    now bounded by MAX_XML_PATH_LENGTH and extended per tag, not re-joined."""

    def _read(self, xml, tagspec="zzz", cls=XMLCorpusView):
        import shutil

        from nltk.data import FileSystemPathPointer
        from nltk.test.unit.security_probes._base import register_data_root

        d = tempfile.mkdtemp()
        undo = register_data_root(d)
        try:
            path = os.path.join(d, "corpus.xml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(xml)
            pointer = FileSystemPathPointer(path)
            if isinstance(tagspec, str):
                return sum(1 for _ in cls(pointer, tagspec))
            stream = pointer.open("utf8")
            try:
                return cls(pointer, "zzz").read_block(stream, tagspec=tagspec)
            finally:
                stream.close()
        finally:
            undo()
            shutil.rmtree(d, ignore_errors=True)

    @pytest.mark.parametrize("kind", ["empty", "startend"])
    def test_the_wide_shape_is_refused(self, kind):
        # the review's reproduction: depth 400, 1000-char names, many siblings
        with pytest.raises(ValueError, match="MAX_XML_PATH_LENGTH"):
            self._read(_wide_xml(400, 1000, 10_000, kind))

    def test_path_at_the_bound_is_accepted(self):
        from nltk.corpus.reader.xmldocs import MAX_XML_PATH_LENGTH

        # _XML_TAG_NAME keeps an empty element's trailing slash in its name (as
        # before the fix), so that path is one char longer than its start tag's.
        a, b = "a" * 2047, "b" * (MAX_XML_PATH_LENGTH - 2048)
        e = "e" * (MAX_XML_PATH_LENGTH - 2049)
        assert self._read(f"<{a}><{b}>x</{b}><{e}/></{a}>") == 0
        with pytest.raises(ValueError, match="MAX_XML_PATH_LENGTH"):
            self._read(f"<{a}><{b}c>x</{b}c></{a}>")
        with pytest.raises(ValueError, match="MAX_XML_PATH_LENGTH"):
            self._read(f"<{a}><{e}c/></{a}>")

    @pytest.mark.parametrize("kind", ["empty", "startend"])
    def test_sibling_walk_under_the_bound_is_linear(self, kind):
        # a 3 KB path (depth 50, 60-char names) and 4x the siblings under it
        _assert_subquadratic(
            lambda n: self._read(_wide_xml(50, 60, n, kind)), 10_000, 40_000
        )

    def test_long_name_siblings_under_the_bound_are_linear(self):
        op = lambda n: self._read(_wide_xml(50, 60, n, "empty", sib_name="m" * 900))
        _assert_subquadratic(op, 2_500, 10_000)

    def test_incremental_path_matches_a_rejoin_at_every_tag(self):
        # Every path handed to the tagspec, over nesting, empty elements at the
        # root and below, siblings and a backtrack, equals the pre-fix re-join.
        xml = (
            "<r/><d><a/><b><c/><c/></b><b>t</b><e></e></d>"
            + "<d><s>x</s>"
            + "<q/>" * 50
            + "<p><p>y</p></p></d>"
        )
        got, ref = _PathRecorder(), _PathRecorder()
        self._read(xml, tagspec=got)
        self._read(xml, tagspec=ref, cls=_PreFixXMLCorpusView)
        assert got.paths == ref.paths and got.paths[:3] == ["/r/", "d", "d/a/"]
        assert self._read("<doc><s>a</s><s>b</s></doc>", ".*/s") == 2

    def test_width_bound_has_teeth(self):
        # The pre-fix walk accepts the shape and the path characters it hands the
        # tagspec grow 16x over a budget split 4x between name length and
        # sibling count; the shipped walk refuses the same shape.
        work = {}
        for u in (1, 4):
            meter = _PathRecorder()
            self._read(
                _wide_xml(400, 100 * u, 1000 * u),
                tagspec=meter,
                cls=_PreFixXMLCorpusView,
            )
            work[u] = sum(len(p) for p in meter.paths)
        assert work[4] / work[1] >= QUADRATIC_RATIO, work
        with pytest.raises(ValueError, match="MAX_XML_PATH_LENGTH"):
            self._read(_wide_xml(400, 100, 1000))
