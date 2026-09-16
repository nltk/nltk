# Natural Language Toolkit: algorithmic-DoS hardening tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Regression tests for four algorithmic denial-of-service defects on untrusted
input (CWE-400/407/674/1333):

* ``redos.check_pattern`` bounds the capturing-group count (quadratic compile).
* ``SeekableUnicodeStreamReader.readline`` reads an unterminated line in linear
  time (was O(N**2) re-splitting the whole growing buffer).
* ``XMLCorpusView.read_block`` bounds XML nesting depth (the per-tag
  ``"/".join(context)`` was O(depth) each, so deep nesting was O(n**2)).
* the WordNet ``Synset`` hypernym walkers refuse a cyclic / over-deep graph
  instead of recursing without bound.

Nothing is mocked: each guard is driven through its real public entry point.
"""

import io
import os
import tempfile

import pytest

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

    def test_unicode_line_separator_still_splits(self):
        # U+2028 is a str.splitlines break; a line ending only in it must split.
        r = self._reader("a\u2028b".encode())
        first = r.readline()
        assert first == "a\u2028"

    def test_many_short_lines_via_linebuffer(self):
        # Exercises the buffered-line prepend path: a completed line left in the
        # linebuffer (it ends in a break) must still be returned when the next
        # block read has no break of its own.
        data = "".join("l%d\n" % i for i in range(60)).encode("utf-8")
        r = self._reader(data)
        assert [r.readline() for _ in range(60)] == ["l%d\n" % i for i in range(60)]

    def test_long_unterminated_line_is_not_quadratic(self):
        # Pre-fix this re-split the whole growing buffer each pass (O(N**2)); an
        # 8 MB single line took ~7s. The linear read is well under a second, so a
        # very generous bound catches a quadratic regression without flaking.
        import time

        r = self._reader(b"a" * 8_000_000)
        start = time.perf_counter()
        line = r.readline()
        assert len(line) == 8_000_000
        assert time.perf_counter() - start < 4.0


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

    def test_deeply_nested_xml_is_refused(self):
        from nltk.corpus.reader.xmldocs import MAX_XML_DEPTH

        depth = MAX_XML_DEPTH + 50
        xml = "<a>" * depth + "x" + "</a>" * depth
        with pytest.raises(ValueError):
            self._view(xml, "zzz")  # non-matching tagspec forces the full descent

    def test_normal_xml_reads(self):
        got = self._view("<doc><s>hi</s><s>bye</s></doc>", ".*/s")
        assert len(got) == 2


# --- #53pg: WordNet hypernym walkers refuse a cyclic graph -------------------


class TestWordNetHypernymCycle:
    WALKERS = ("max_depth", "min_depth", "hypernym_paths", "hypernym_distances")

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
            with pytest.raises(ValueError):
                getattr(a, walker)()
        finally:
            for n, fn in saved.items():
                setattr(Synset, n, fn)
            for m in ("_max_depth", "_min_depth"):
                a.__dict__.pop(m, None)
                b.__dict__.pop(m, None)

    @pytest.mark.parametrize("walker", WALKERS)
    def test_real_acyclic_graph_still_works(self, walker):
        wn = self._wn()
        result = getattr(wn.synset("dog.n.01"), walker)()
        assert result  # non-empty depth / paths / distances


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
        import time

        from nltk import redos

        start = time.perf_counter()
        redos.match(self.PAT, "(" * 200_000)  # was catastrophic (5s timeout)
        assert time.perf_counter() - start < 2.0

    def test_real_wordnet_lemmas_load(self):
        wn = pytest.importorskip("nltk.corpus").wordnet
        try:
            wn.synset("dog.n.01")
        except LookupError:
            pytest.skip("wordnet corpus not downloaded")
        assert [l.name() for l in wn.synset("dog.n.01").lemmas()][0] == "dog"


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
        text = 'She said "hi" and "bye" to "all".'
        for tk in self._tokenizers():
            spans = list(tk.span_tokenize(text))
            assert spans and all(0 <= a <= b <= len(text) for a, b in spans)
            assert all(text[a:b] for a, b in spans)

    def test_many_quotes_is_not_quadratic(self):
        import time

        from nltk.tokenize.destructive import NLTKWordTokenizer

        start = time.perf_counter()
        list(NLTKWordTokenizer().span_tokenize('"' * 40000))
        assert time.perf_counter() - start < 4.0


class TestLegalitySyllableTokenLen:
    def _lp(self):
        from nltk.tokenize import LegalitySyllableTokenizer

        return LegalitySyllableTokenizer(["wonderful", "sentence", "this", "is"])

    def test_normal_token_syllabifies(self):
        assert self._lp().tokenize("wonderful")

    def test_oversized_token_is_refused(self):
        from nltk.tokenize import LegalitySyllableTokenizer

        with pytest.raises(ValueError):
            self._lp().tokenize("a" * (LegalitySyllableTokenizer.MAX_TOKEN_LEN + 1))


class TestSteppingParserDeadline:
    def _grammar(self, s):
        from nltk import CFG

        return CFG.fromstring(s)

    def test_normal_grammar_parses(self):
        from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

        g = self._grammar("S -> NP VP\nNP -> 'the' 'dog'\nVP -> 'runs'")
        assert list(SteppingRecursiveDescentParser(g).parse(["the", "dog", "runs"]))

    def test_left_recursive_grammar_times_out(self):
        from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

        g = self._grammar("S -> S 'a'\nS -> 'a'")
        p = SteppingRecursiveDescentParser(g, max_time=1)
        with pytest.raises((TimeoutError, RecursionError)):
            list(p.parse(["a", "a", "a", "a"]))


# --- re-anchoring quadratic regex class (ycoe #3896 + the whole family) -------


class TestSensevalFixXMLLinear:
    """senseval._fixXML strips XML tags with re-anchoring subs; the tag bodies are
    now {0,N}-bounded, so a crafted block is linear rather than O(n**2)."""

    def test_crafted_block_is_linear(self):
        import time

        from nltk.corpus.reader.senseval import _fixXML

        start = time.perf_counter()
        _fixXML("<snum=" * 40000)
        _fixXML("<!DOCTYPE" + "a" * 40000)
        assert time.perf_counter() - start < 3.0

    def test_doctype_still_stripped(self):
        from nltk.corpus.reader.senseval import _fixXML

        assert "DOCTYPE" not in _fixXML('<!DOCTYPE corpus SYSTEM "x.dtd">tail')


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
