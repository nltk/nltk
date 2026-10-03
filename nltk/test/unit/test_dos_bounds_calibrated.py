# Natural Language Toolkit: calibrated algorithmic-DoS bounds
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Every bound the DoS hardening introduces, calibrated on real data and
driven through its real entry point (CWE-400/407/674/1333).

Each regex site that turned an unbounded run (``.*``, ``[^>]*``, ``\\w+``) into
a ``{0,N}`` run was measured against the real corpus, grammar, valuation or
model it serves (the quantity the bound limits, over every input that reaches
the regex), and every length, depth and path cap likewise. The calibration is
recorded per site in ``_SITES`` below and checked here with, for every bound:

* at the bound: the shipped form matches, byte-identical to the pre-fix form;
* one over, and far over: no match (or a clear refusal), still linear;
* the real-data maximum, in the real shape, as a must-pass benign case;
* the re-anchoring trigger with the required literal absent AND present once
  (the engine's literal prefilter hides a quadratic otherwise), both linear;
* teeth: the verbatim pre-fix form, on the same trigger at a size where it ran
  past 5 s untimed, runs into a 0.5 s backstop.

A bound that silently changed a parse (an oversized dependency terminal, an
oversized valuation tuple) now refuses with a ValueError instead, and the
refusal is itself linear. Nothing is mocked; where a corpus is needed and not
installed the one test that reads it is skipped, never the bound checks.
"""

import functools
import inspect
import os

import pytest

from nltk import redos
from nltk.test.unit import timing

_linear = functools.partial(timing.assert_subquadratic, cpu_bound=True, reps=2)


def _apply(rx, op, s):
    if op == "findall":
        return rx.findall(s)
    if op == "sub":
        return rx.sub("", s)
    if op == "sub1":
        return rx.sub(r"\1", s)
    if op == "split":
        return rx.split(s)
    if op == "finditer":
        return [(m.span(), m.groups()) for m in rx.finditer(s)]
    raise AssertionError(op)


def _matched(op, got, s):
    """The op found something: findall/finditer returned matches, sub changed
    the input, split cut it."""
    if op in ("findall", "finditer"):
        return bool(got)
    if op == "split":
        return len(got) > 1
    return got != s


def _source_has(module_name, literal):
    """The inline pattern under test is the one the module ships."""
    import importlib

    src = inspect.getsource(importlib.import_module(module_name))
    assert literal in src, (module_name, literal)


# The calibration table, name: (module, shipped pattern or attribute, pre-fix
# pattern, op, bound, at_bound(n), real-data maximum, real-shaped input, data
# source, trigger(n) literal absent, trigger_present(n), pre-fix size past 5 s)

_S = {}


def _site(name, **kw):
    kw.setdefault("marker", lambda n: "a" * n)  # the oversized quantity itself
    kw.setdefault("teeth_trigger", kw["trigger"])
    _S[name] = kw


_site(
    "pl196x.attr",
    module="nltk.corpus.reader.pl196x",
    attr="PARA",
    prefix=r"<p(?: [^>]*){0,1}>(.*?)</p>",
    op="findall",
    bound=1024,
    at=lambda n: "<p " + "a" * n + ">x</p>",
    real=337,
    real_input='<w id="wp192502" lemma="rozegrany" ana="'
    + " ".join(["ASIPP--------P"] * 20)[
        : 337 - len('id="wp192502" lemma="rozegrany" ana="') - 1
    ]
    + '">rozegranym</w>',
    real_attr="WORD",
    data="pl196x corpus, all ten files (a <w> carrying id, lemma and a 300-char ana)",
    trigger=lambda n: "<p " * n,
    trigger_present=lambda n: "<p " * n + "></p>",
    prefix_n=8000,
)
_site(
    "pl196x.body_run",
    module="nltk.corpus.reader.pl196x",
    attr="PARA",
    prefix=r"<p(?: [^>]*){0,1}>(.*?)</p>",
    op="findall",
    bound=4096,
    at=lambda n: "<p>" + "x" * n + "</p>",
    marker=lambda n: "x" * n,
    real=350,
    real_input="<p><s>" + "x" * 350 + "</s></p>",
    data="pl196x corpus: the longest run between two `<` inside a <p>",
    trigger=lambda n: "<p>" * n,
    trigger_present=lambda n: "<p>" * n + "</p>",
    prefix_n=64000,
)
_site(
    "pl196x.body_pieces",
    module="nltk.corpus.reader.pl196x",
    attr="PARA",
    prefix=r"<p(?: [^>]*){0,1}>(.*?)</p>",
    op="findall",
    bound=16384,
    at=lambda n: "<p>"
    + "<s>" * ((n + 1) // 2)
    + "</p>",  # pieces: a `<` and a run each
    marker=lambda n: "<s>" * ((n + 1) // 2),
    teeth_trigger=lambda n: "<p>" * n,
    real=577,
    real_input="<p>"
    + ('<s><w id="dr073101" lemma="niegdys" ana="D------------P">niegdys</w></s>' * 100)
    + "</p>",  # 10499 chars, 600 pieces, as the longest real paragraph (10399, 577)
    data="pl196x corpus: the longest <p> body (10399 chars, 577 pieces)",
    trigger=lambda n: "<p>" + "<s>" * n,
    trigger_present=lambda n: "<p>" + "<s>" * n + "</p>",
    prefix_n=64000,
)
_site(
    "pl196x.word",
    module="nltk.corpus.reader.pl196x",
    attr="WORD",
    prefix=r"<[wc](?: [^>]*){0,1}>(.*?)</[wc]>",
    op="findall",
    bound=1024,
    at=lambda n: "<w>" + "x" * n + "</w>",
    marker=lambda n: "x" * n,
    real=41,
    real_input='<w id="pu064651" lemma="" ana="XXXXXXXXXXXXXP">Institutiones iuris publici ecclesiastici</w>',
    data="pl196x corpus: the longest <w>/<c> body",
    trigger=lambda n: "<w>" * n,
    trigger_present=lambda n: "<w>" * n + "</w>",
    prefix_n=64000,
)
_site(
    "alpino.sentence",
    module="nltk.corpus.reader.bracket_parse",
    literal=r"<sentence>(?:(?!<sentence>).){0,8192}</sentence>",
    prefix=r"<sentence>.*</sentence>",
    op="sub",
    bound=8192,
    at=lambda n: "<sentence>" + "x" * n + "</sentence>",
    marker=lambda n: "x" * n,
    real=512,
    real_input="<sentence>"
    + "De PvdA-Kamerleden drs. Ed van Thijn en E. R. Wieldraaijer " * 8
    + "x</sentence>",
    data="alpino corpus, all 21569 trees",
    trigger=lambda n: "<sentence>" * n,
    trigger_present=lambda n: "<sentence>" * n + "</sentence>",
    prefix_n=16000,
)
_site(
    "alpino.alpino_ds",
    module="nltk.corpus.reader.bracket_parse",
    literal=r"</?alpino_ds[^<>]{0,1024}>",
    prefix=r"</?alpino_ds.*>",
    op="sub",
    bound=1024,
    at=lambda n: "<alpino_ds" + "a" * n + ">",
    real=24,
    real_input='<alpino_ds version="1.2" id="0001">',
    data="alpino corpus, all 21569 trees",
    trigger=lambda n: "<alpino_ds" * n,
    trigger_present=lambda n: "<alpino_ds" * n + ">",
    prefix_n=16000,
)
_site(
    "alpino.attr",
    module="nltk.corpus.reader.bracket_parse",
    attr="ALPINO_ATTR",
    prefix=r'(\w+)="([^"]*)"',
    op="findall",
    bound=64,
    at=lambda n: "a" * n + '="v"',
    real=5,
    real_input='word="televisie-voorlichtingsprogramma&apos;s" begin="0"',
    data="alpino corpus, all 697032 node lines (longest name 5, value 39)",
    trigger=lambda n: "a" * n,
    trigger_present=lambda n: "a" * n + '="',
    teeth_trigger=lambda n: "a" * n
    + '="',  # the literal absent, the prefilter hides it
    prefix_n=32000,
)
_site(
    "verbnet.member_tail",
    module="nltk.corpus.reader.verbnet",
    attr=("VerbnetCorpusReader", "_INDEX_RE"),
    prefix=r'<MEMBER name="\??([^"]+)" wn="([^"]*)"[^>]+>|<VNSUBCLASS ID="([^"]+)"/?>',
    op="finditer",
    bound=1024,
    at=lambda n: '<MEMBER name="a" wn="b"' + "x" * n + ">",
    marker=lambda n: "x" * n,
    real=78,
    real_input='<MEMBER name="drift" wn="drift%2:38:02 drift%2:38:04" '
    'grouping="drift.01 drift.02 drift.04" features="+speed +path_shape +purpose"/>',
    data="verbnet and verbnet3, all 562 class files (tail 78, whole tag 219)",
    trigger=lambda n: '<MEMBER name="a" wn="" ' * n,
    trigger_present=lambda n: '<MEMBER name="a" wn="" ' * n + ">",
    prefix_n=16000,
)
_site(
    "lin.key",
    module="nltk.corpus.reader.lin",
    attr=("LinThesaurusCorpusReader", "_key_re"),
    prefix=r'\("?([^"]+)"? \(desc [0-9.]+\).+',
    op="sub1",
    bound=512,
    at=lambda n: '("' + "k" * n + '" (desc 3844.85) (sims',
    marker=lambda n: "k" * n,
    real=64,
    real_input='("United Nations Educational, Scientific and Cultural Organization" (desc 3844.85) (sims',
    data="lin_thesaurus, all 60878 entries of the three files",
    trigger=lambda n: "(" * n,
    trigger_present=lambda n: "(" * n + '" (desc 1) x',
    prefix_n=8000,
)
_site(
    "nkjp.token",
    module="nltk.corpus.reader.nkjp",
    literal=r"nkjp:(?:(?!nkjp:)[^ ]){0,256} ",
    prefix=r"nkjp:[^ ]* ",
    op="split",
    bound=256,
    at=lambda n: "nkjp:" + "a" * n + " ",
    real=15,
    real_input='<f name="interpretation" nkjp:rejected="true" nkjp:manual="true" >',
    data="NKJP 1M-word sample, all 30177 XML files (76M lines)",
    trigger=lambda n: "nkjp:" * n,
    trigger_present=lambda n: "nkjp:" * n + " ",
    prefix_n=16000,
)
_site(
    "reviews.feature_word",
    module="nltk.corpus.reader.reviews",
    attr="FEATURES",
    prefix=r"(\w+(?:\s\w+){0,50})\[((?:\+|\-)\d)\]",
    op="findall",
    bound=80,
    at=lambda n: "a" * n + "[+2]",
    real=16,
    real_input="unresponsiveness[-2]##the camera is unresponsive",
    data="product_reviews_1 and product_reviews_2, all 16694 feature lines",
    trigger=lambda n: "a" * n,
    trigger_present=lambda n: "a" * n + "[",
    teeth_trigger=lambda n: "a" * n + "[",  # the literal absent, the prefilter hides it
    prefix_n=8000,
)
_senseval = "nltk.corpus.reader.senseval"
_site(
    "senseval.snum_prefix",
    module=_senseval,
    literal=r'(<[^<]{0,256}snum=)([^"<>]{1,256})>',
    prefix=r'(<[^<]*snum=)([^">]+)>',
    op="sub1",
    bound=256,
    at=lambda n: "<" + "a" * n + "snum=12>",
    real=0,
    real_input="<s snum=12>",
    data="senseval corpus, all 15225 instances: the shipped files are already repaired, no match",
    trigger=lambda n: "<snum=" * n,
    trigger_present=lambda n: "<snum=" * n + "1>",
    prefix_n=16000,
)
_site(
    "senseval.snum_value",
    module=_senseval,
    literal=r'(<[^<]{0,256}snum=)([^"<>]{1,256})>',
    prefix=r'(<[^<]*snum=)([^">]+)>',
    op="sub1",
    bound=256,
    at=lambda n: "<s snum=" + "1" * n + ">",
    marker=lambda n: "1" * n,
    real=0,
    real_input="<s snum=12>",
    data="senseval corpus: no match in the shipped files",
    trigger=lambda n: "<snum=" * n,
    trigger_present=lambda n: "<snum=" * n + "1>",
    prefix_n=16000,
)
_site(
    "senseval.ampI",
    module=_senseval,
    literal=r"<\&I[^<>]{0,256}>",
    prefix=r"<\&I[^>]*>",
    op="sub",
    bound=256,
    at=lambda n: "<&I" + "a" * n + ">",
    real=0,
    real_input="<&I .>",
    data="senseval corpus: no match in the shipped files",
    trigger=lambda n: "<&I" * n,
    trigger_present=lambda n: "<&I" * n + ">",
    prefix_n=32000,
)
_site(
    "senseval.brace",
    module=_senseval,
    literal=r"<{([^<}]{1,256})}>",
    prefix=r"<{([^}]+)}>",
    op="sub1",
    bound=256,
    at=lambda n: "<{" + "a" * n + "}>",
    real=0,
    real_input="<{word}>",
    data="senseval corpus: no match in the shipped files",
    trigger=lambda n: "<{" * n,
    trigger_present=lambda n: "<{" * n + "}>",
    prefix_n=64000,
)
_site(
    "senseval.doctype",
    module=_senseval,
    literal=r"<!DOCTYPE[^<>]{0,1024}>",
    prefix=r"<!DOCTYPE[^>]*>",
    op="sub",
    bound=1024,
    at=lambda n: "<!DOCTYPE" + "a" * n + ">",
    real=0,
    real_input='<!DOCTYPE corpus SYSTEM "lexical-sample.dtd">',
    data="senseval corpus: no match in the shipped files",
    trigger=lambda n: "<!DOCTYPE" * n,
    trigger_present=lambda n: "<!DOCTYPE" * n + ">",
    prefix_n=16000,
)
_site(
    "senseval.bracket",
    module=_senseval,
    literal=r"<\[\/?[^<>]{1,256}\]*>",
    prefix=r"<\[\/?[^>]+\]*>",
    op="sub",
    bound=256,
    at=lambda n: "<[" + "a" * n + "]>",
    real=0,
    real_input="<[hi]> <[/p]>",
    data="senseval corpus: no match in the shipped files",
    trigger=lambda n: "<[" * n,
    trigger_present=lambda n: "<[" * n + "]>",
    prefix_n=8000,
)
_site(
    "ieer.tag",
    module="nltk.chunk.util",
    literal=r"<[^<>]{1,400}>|[^\s<]+",
    prefix=r"<[^>]+>|[^\s<]+",
    op="finditer",
    bound=400,
    at=lambda n: "<" + "a" * n + ">",
    real=47,
    real_input='<b_enamex type="ORGANIZATION" alt="Red Crescent">Red Crescent<e_enamex>',
    data="ieer corpus, all 94 documents",
    trigger=lambda n: "<" * n,
    trigger_present=lambda n: "<" * n + ">",
    prefix_n=64000,
)
_site(
    "ace.tag",
    module="nltk.chunk.named_entity",
    literal=r"<(?!/?TEXT)[^<>]{1,400}>",
    prefix=r"<(?!/?TEXT)[^>]+>",
    op="sub",
    bound=400,
    at=lambda n: "<" + "a" * n + ">",
    real=None,
    real_input='<DOC>\n<DOCNO> APW20001227.0001 </DOCNO>\n<DOCTYPE SOURCE="newswire"> NEWS STORY '
    "</DOCTYPE>\n<DATETIME> 2000-12-27 </DATETIME>\n<BODY>\n<HEADLINE>x</HEADLINE>\n<TEXT>",
    data="not measured: the ACE 2004 corpus is licensed and not shipped (the format's tags are the IEER-style ones above)",
    trigger=lambda n: "<" * n,
    trigger_present=lambda n: "<" * n + ">",
    prefix_n=64000,
)
_site(
    "ycoe.code_node",
    module="nltk.corpus.reader.ycoe",
    literal=r"(?u)\((CODE|ID)[^()]{0,400}\)",
    prefix=r"(?u)\((CODE|ID)[^\)]*\)",
    op="sub",
    bound=400,
    at=lambda n: "(CODE" + "a" * n + ")",
    real=None,
    real_input="( (IP-MAT (NP-NOM (PRO^N Ic)) (VBP wat)) (ID cotest,1.1))",
    data="not measured: the YCOE corpus is licensed and only its README is shipped",
    trigger=lambda n: "(CODE" * n,
    trigger_present=lambda n: "(CODE" * n + ")",
    prefix_n=32000,
)
_site(
    "evaluate.tuple",
    module="nltk.sem.evaluate",
    attr="_TUPLES_RE",
    prefix=r"(?:(?<!\s)\s*)?(\([^)]+\))\s*",
    op="findall",
    bound=1024,
    at=lambda n: "(" + "a" * n + ")",
    real=8,
    real_input="(b1, g1), (b2, g1), (g1, d1), (g2, d2)",
    data="grammars/sample_grammars/valuation1.val, the semantics doctests and the sem demos",
    trigger=lambda n: "(" * n,
    trigger_present=lambda n: "(" * n + ")",
    prefix_n=64000,
)
_site(
    "grammar.dg_token",
    module="nltk.grammar",
    attr="_SPLIT_DG_RE",
    prefix=r"""('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)""",
    op="split",
    bound=512,
    at=lambda n: "'" + "a" * n + "' -> 'b'",
    real=9,
    real_input="'play' -> 'golf' | 'dachshund' | 'to'",
    data="the dependency doctests, the three parser demos and the parser tests",
    trigger=lambda n: "-" * n,
    trigger_present=lambda n: "-" * n + ">",
    prefix_n=32000,
)


def _shipped(site):
    import importlib

    mod = importlib.import_module(site["module"])
    if "literal" in site:
        _source_has(site["module"], site["literal"])
        return redos.compile(site["literal"])
    attr = site["attr"]
    if isinstance(attr, tuple):
        return getattr(getattr(mod, attr[0]), attr[1])
    return getattr(mod, attr)


def _prefix(site):
    flags = 0
    if site["module"] == "nltk.sem.evaluate":
        import re

        flags = re.VERBOSE
    return redos.compile(site["prefix"], flags)


_NAMES = sorted(_S)


class TestRegexBoundsCalibrated:
    @pytest.mark.parametrize("name", _NAMES)
    def test_at_the_bound_identical_to_prefix_one_over_no_match(self, name):
        site = _S[name]
        new, old, op, b = _shipped(site), _prefix(site), site["op"], site["bound"]
        at = site["at"](b)
        got = _apply(new, op, at)
        assert got == _apply(old, op, at)
        assert _matched(op, got, at), name
        # one over the bound, and far over: the pre-fix form captures the
        # oversized run, the shipped form never does (the only difference),
        # and the refusal stays linear
        for n in (b + 1, 50 * b):
            over, marker = site["at"](n), site["marker"](n)
            assert _apply(new, op, over) != _apply(old, op, over), name
            old_hits = [m.group() for m in old.finditer(over) if marker in m.group()]
            assert old_hits, name  # the pre-fix form swallows the oversized run
            new_hits = [m.group() for m in new.finditer(over)]
            assert not any(h in new_hits for h in old_hits), (name, new_hits[:2])
        _linear(lambda n: _apply(new, op, site["at"](n)), 20 * b, 80 * b)

    @pytest.mark.parametrize("name", _NAMES)
    def test_real_data_maximum_is_benign(self, name):
        site = _S[name]
        new, old, op = _shipped(site), _prefix(site), site["op"]
        if site.get("real_attr"):
            import importlib

            new = getattr(importlib.import_module(site["module"]), site["real_attr"])
            old = redos.compile(r"<[wc](?: [^>]*){0,1}>(.*?)</[wc]>")
        real = site["real_input"]
        got = _apply(new, op, real)
        assert got == _apply(old, op, real), name
        assert _matched(op, got, real), name
        if site["real"]:
            # the real maximum sits inside the bound with margin
            assert site["real"] < site["bound"], name

    @pytest.mark.parametrize("name", _NAMES)
    def test_trigger_is_linear_literal_absent_and_present(self, name):
        site = _S[name]
        new, op = _shipped(site), site["op"]
        _linear(lambda n: _apply(new, op, site["trigger"](n)), 25_000, 100_000)
        _linear(lambda n: _apply(new, op, site["trigger_present"](n)), 25_000, 100_000)

    @pytest.mark.parametrize("name", _NAMES)
    def test_prefix_form_has_teeth(self, name, monkeypatch):
        # Untimed, the pre-fix form ran past 5 s at prefix_n on this trigger;
        # the shipped form finishes it well inside a 0.5 s backstop.
        site = _S[name]
        new, old, op = _shipped(site), _prefix(site), site["op"]
        trig = site["teeth_trigger"](site["prefix_n"])
        monkeypatch.setattr(redos, "DEFAULT_TIMEOUT", 0.5)
        _apply(new, op, trig)
        with pytest.raises(TimeoutError):
            _apply(old, op, trig)


class TestPl196xRealCorpus:
    def test_corpus_words_equal_the_prefix_patterns_and_keep_every_paragraph(
        self, monkeypatch
    ):
        # The earlier {0,8192} body silently dropped the four paragraphs over
        # 8 KB; the calibrated form reads every block as the pre-fix one did.
        import nltk.data
        from nltk.corpus.reader import pl196x
        from nltk.corpus.reader.pl196x import Pl196xCorpusReader, TEICorpusView

        try:
            path = nltk.data.find(
                "corpora/pl196x/e-dramat.xml"
            )  # 33 paragraphs over 8 KB
        except LookupError:
            pytest.skip("pl196x corpus not downloaded")
        head_len = Pl196xCorpusReader.head_len

        def read():
            return list(TEICorpusView(path, False, True, True, head_len=head_len))

        shipped = read()
        assert len(shipped) >= 2000  # every <p> of the file's <text> blocks
        monkeypatch.setattr(
            pl196x, "PARA", redos.compile(r"<p(?: [^>]{0,1024}){0,1}>(.{0,8192}?)</p>")
        )
        assert len(read()) <= len(shipped) - 33  # the earlier bound dropped them
        prefix = {
            "PARA": r"<p(?: [^>]*){0,1}>(.*?)</p>",
            "SENT": r"<s(?: [^>]*){0,1}>(.*?)</s>",
            "WORD": r"<[wc](?: [^>]*){0,1}>(.*?)</[wc]>",
        }
        for name, pat in prefix.items():
            monkeypatch.setattr(pl196x, name, redos.compile(pat))
        assert read() == shipped


class TestDependencyGrammarRefusal:
    """An oversized quoted terminal or arrow is refused up front (the validator
    and the splitter carry the same bounds), never built into an epsilon
    production with the token missing."""

    def _parse(self, src):
        from nltk.grammar import DependencyGrammar

        return DependencyGrammar.fromstring(src)

    def test_at_the_bound_parses_as_before(self):
        dg = self._parse("'" + "a" * 512 + "' -> 'b'\n'b' -> " + "'" + "c" * 512 + "'")
        assert dg.contains("a" * 512, "b") and dg.contains("b", "c" * 512)
        assert self._parse("'a' " + "-" * 7 + "> 'b'").contains("a", "b")

    @pytest.mark.parametrize("n", [513, 600, 100_000])
    def test_one_over_and_far_over_are_refused(self, n):
        with pytest.raises(ValueError, match="512"):
            self._parse("'" + "a" * n + "' -> 'b'")
        with pytest.raises(ValueError, match="512"):
            self._parse("'a' -> '" + "b" * n + "'")
        with pytest.raises(ValueError, match="512"):
            self._parse("'a' -> \"" + "b" * n + '"')

    def test_oversized_arrow_is_refused(self):
        with pytest.raises(ValueError, match="8"):
            self._parse("'a' " + "-" * 9 + "> 'b'")

    def test_refusal_is_linear(self):
        def refuse(n):
            with pytest.raises(ValueError):
                self._parse("'" + "a" * n + "' -> 'b'")

        _linear(refuse, 50_000, 200_000)

    def test_real_grammars_parse_identically_to_the_prefix_forms(self, monkeypatch):
        import nltk.grammar as G

        srcs = [
            "'scratch' -> 'cats' | 'walls'\n'walls' -> 'the'\n'cats' -> 'the'",
            "'fell' -> 'price' | 'stock'\n'price' -> 'of'\n'stock' -> 'fell'",
            "'play' -> 'golf' | 'dachshund' | 'to'\n'golf' -> 'with'",
        ]
        shipped = [str(self._parse(s)) for s in srcs]
        prefix_read = redos.compile(
            r"""^\s*('[^']+')\s*(?:[-=]+>)\s*(?:("[^"]+"|'[^']+'|\|)\s*)*$"""
        )
        monkeypatch.setattr(G, "_READ_DG_RE", prefix_read)
        monkeypatch.setattr(
            G, "_SPLIT_DG_RE", redos.compile(r"""('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)""")
        )
        assert [str(self._parse(s)) for s in srcs] == shipped

    def test_refusal_has_teeth(self, monkeypatch):
        # With both pre-fix forms restored the 513-char terminal is accepted
        # and parsed whole; with only the validator restored the splitter's gap
        # check still refuses it rather than building an epsilon production.
        import nltk.grammar as G

        src = "'" + "a" * 513 + "' -> 'b'"
        prefix_read = redos.compile(
            r"""^\s*('[^']+')\s*(?:[-=]+>)\s*(?:("[^"]+"|'[^']+'|\|)\s*)*$"""
        )
        monkeypatch.setattr(G, "_READ_DG_RE", prefix_read)
        with pytest.raises(ValueError, match="cannot capture"):
            self._parse(src)
        monkeypatch.setattr(
            G, "_SPLIT_DG_RE", redos.compile(r"""('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)""")
        )
        assert self._parse(src).contains("a" * 513, "b")


class TestValuationTupleRefusal:
    """An oversized or unclosed tuple expression is refused with a ValueError
    naming MAX_TUPLE_LENGTH, never read as comma-separated scalars."""

    def _tuple(self, chars):
        inner = ", ".join("e%d" % i for i in range(10**6))[: chars - 2]
        return "(" + inner.rsplit(",", 1)[0] + ")"

    def test_at_the_bound_parses_as_before(self, monkeypatch):
        from nltk.sem import evaluate as E

        tup = "(" + "e" * 1024 + ")"  # the {1,1024} run exactly
        val = dict(E.read_valuation("r => {" + tup + "}"))["r"]
        assert val == {("e" * 1024,)}
        long = self._tuple(1000)
        assert len(dict(E.read_valuation("r => {" + long + "}"))["r"]) == 1

    @pytest.mark.parametrize("chars", [1027, 1500, 200_000])
    def test_one_over_and_far_over_are_refused(self, chars):
        from nltk.sem import evaluate as E

        tup = "(" + "e" * (chars - 2) + ")"
        with pytest.raises(ValueError, match="MAX_TUPLE_LENGTH"):
            E._read_valuation_line("r => {" + tup + "}")
        with pytest.raises(ValueError, match="MAX_TUPLE_LENGTH"):
            E.read_valuation("r => {" + tup + "}")

    def test_unclosed_tuple_is_refused_not_split(self):
        from nltk.sem import evaluate as E

        for bad in ("r => {(a, b}", "r => {a(b, c}", "r => {(a, (b), c)}"):
            with pytest.raises(ValueError, match="MAX_TUPLE_LENGTH"):
                E.read_valuation(bad)

    def test_refusal_is_linear(self):
        from nltk.sem import evaluate as E

        def refuse(n):
            with pytest.raises(ValueError):
                E._read_valuation_line("r => {(" + "e" * n + ")}")

        _linear(refuse, 50_000, 200_000)
        _linear(lambda n: E._TUPLES_RE.findall("(" * n + ")"), 50_000, 200_000)

    def test_real_valuations_parse_identically_to_the_prefix_form(self, monkeypatch):
        import re

        import nltk.data
        from nltk.sem import evaluate as E

        srcs = [
            "boy => {b1, b2}\ngirl => {g1, g2}\nchase => {(b1, g1), (b2, g1), (g1, d1), (g2, d2)}",
            "a => b\nempty => {}\nsee => {(b1, g1)}\nmany => {(b1, g1), (g2, d2),(g3, d3)}",
        ]
        try:
            srcs.append(
                open(nltk.data.find("grammars/sample_grammars/valuation1.val")).read()
            )
        except LookupError:
            pass
        shipped = [dict(E.read_valuation(s)) for s in srcs]
        monkeypatch.setattr(
            E,
            "_TUPLES_RE",
            redos.compile(r"(?:(?<!\s)\s*)?(\([^)]+\))\s*", re.VERBOSE),
        )
        assert [dict(E.read_valuation(s)) for s in srcs] == shipped
        assert shipped[0]["chase"] == {
            ("b1", "g1"),
            ("b2", "g1"),
            ("g1", "d1"),
            ("g2", "d2"),
        }

    def test_refusal_has_teeth(self, monkeypatch):
        import re

        from nltk.sem import evaluate as E

        src = "r => {" + self._tuple(1500) + "}"
        with pytest.raises(ValueError, match="MAX_TUPLE_LENGTH"):
            E.read_valuation(src)
        monkeypatch.setattr(
            E,
            "_TUPLES_RE",
            redos.compile(r"(?:(?<!\s)\s*)?(\([^)]+\))\s*", re.VERBOSE),
        )
        assert len(list(dict(E.read_valuation(src))["r"])[0]) == 268


class TestLegalityTokenizerCalibrated:
    _VOCAB = "the cat sat on a mat with strong string spring sprat".split() * 20

    def _lp(self):
        from nltk.tokenize import LegalitySyllableTokenizer

        return LegalitySyllableTokenizer(self._VOCAB)

    def _reference(self, lp, token):
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

    def test_real_maximum_token_and_the_bound(self):
        lp = self._lp()
        real = "nnuolapertar-it-vuh-karti-birifw-"  # the longest token of words + brown
        assert len(real) == 33
        assert lp.tokenize(real) == self._reference(lp, real)
        at = "strab" * (lp.MAX_TOKEN_LEN // 5) + "a" * (lp.MAX_TOKEN_LEN % 5)
        assert len(at) == lp.MAX_TOKEN_LEN
        assert lp.tokenize(at) == self._reference(lp, at)
        with pytest.raises(ValueError, match="MAX_TOKEN_LEN"):
            lp.tokenize(at + "a")
        with pytest.raises(ValueError, match="MAX_TOKEN_LEN"):
            lp.tokenize("a" * 10**6)

    def test_lying_str_subclass_cannot_make_the_loop_quadratic(self):
        # A str whose len() lies slips past the length cap; the loop behind it
        # is linear on its own (the onset is saturated at the longest legal
        # one), so the cap is defence in depth, not the guard.
        class Lying(str):
            def __len__(self):
                return 1

        lp = self._lp()
        big = Lying("a" * 20_000)
        assert lp.tokenize(big) == self._reference(lp, "a" * 20_000)
        _linear(lambda n: lp.tokenize(Lying("a" * n)), 50_000, 200_000)

    def test_words_corpus_maximum_onset(self):
        from nltk.corpus import words
        from nltk.tokenize import LegalitySyllableTokenizer

        try:
            wl = words.words()
        except LookupError:
            pytest.skip("words corpus not downloaded")
        lp = LegalitySyllableTokenizer(wl)
        assert max(map(len, lp.legal_onsets)) == 3
        for tok in (
            "wonderful",
            "sentence",
            "strengths",
            "nnuolapertar-it-vuh-karti-birifw-",
        ):
            assert lp.tokenize(tok) == self._reference(lp, tok)


class TestXMLCorpusViewCalibrated:
    """MAX_XML_DEPTH 500 against a real maximum of 26 (alpino), and
    MAX_XML_PATH_LENGTH 4096 against 149 chars (mte_teip5), over every XML file
    of the shipped corpora plus semcor, propbank, nombank and both framenets."""

    @pytest.fixture(autouse=True)
    def _fixture_root(self, tmp_path):
        # A corpus file lives inside a registered data root: a bare temp dir
        # is refused by pathsec on Linux (/tmp is shared), as it should be.
        from nltk.test.unit.security_probes._base import register_data_root

        self._root = tmp_path
        self._n = 0
        undo = register_data_root(str(tmp_path))
        try:
            yield
        finally:
            undo()

    def _read(self, text, tagspec="(?!x)x"):
        from nltk.corpus.reader.xmldocs import XMLCorpusView

        self._n += 1
        path = self._root / ("doc%d.xml" % self._n)
        path.write_text(text, encoding="utf-8")
        return list(XMLCorpusView(str(path), tagspec))

    @staticmethod
    def _nested(depth, name="a", inner=""):
        return "<%s>" % name * depth + inner + "</%s>" % name * depth

    def test_depth_at_the_bound_reads_and_one_over_is_refused(self):
        from nltk.corpus.reader.xmldocs import MAX_XML_DEPTH

        got = self._read(self._nested(MAX_XML_DEPTH - 1, inner="<b>x</b>"), "(a/)*b")
        assert [(e.tag, e.text) for e in got] == [("b", "x")]  # b sits at depth 500
        with pytest.raises(ValueError, match="MAX_XML_DEPTH"):
            self._read(self._nested(MAX_XML_DEPTH + 1))
        with pytest.raises(ValueError, match="MAX_XML_DEPTH"):
            self._read(self._nested(50 * MAX_XML_DEPTH))

    def test_path_at_the_bound_reads_and_one_over_is_refused(self):
        from nltk.corpus.reader.xmldocs import MAX_XML_PATH_LENGTH

        assert MAX_XML_PATH_LENGTH == 4096
        name = "n" * 1023  # 4 levels: 4 * 1023 + 3 separators == 4095 chars
        with pytest.raises(ValueError, match="MAX_XML_PATH_LENGTH"):
            self._read(self._nested(4, name, inner="<b>x</b>"))  # b's path 4097
        name = "n" * 1022  # 4 * 1022 + 3 == 4091 chars, b's path 4093
        got = self._read(self._nested(4, name, inner="<b>x</b>"), "(%s/)*b" % name)
        assert [(e.tag, e.text) for e in got] == [("b", "x")]
        name = "n" * 4094  # one element whose path is exactly the cap
        got = self._read(self._nested(1, name, inner="<b>x</b>"), name + "/b")
        assert [(e.tag, e.text) for e in got] == [("b", "x")]
        with pytest.raises(ValueError, match="MAX_XML_PATH_LENGTH"):
            self._read(self._nested(1, "n" * 4095, inner="<b>x</b>"))

    def test_real_maximum_shape_reads_identically_to_a_dom_parse(self):
        # depth 26 (alpino node nesting), path 149 chars, 24-char tag names
        from nltk.xmlsec import fromstring

        name = "writingSystemDeclaration"  # 24 chars, pl196x
        doc = self._nested(26, "node", inner=f"<{name}>x</{name}>" * 3)
        got = self._read(doc, "(node/)*" + name)
        assert [(e.tag, e.text) for e in got] == [(name, "x")] * 3
        assert len(fromstring(doc).findall(".//" + name)) == 3

    def test_under_cap_wide_shape_is_linear_in_siblings(self):
        name = "a" * 1000  # path 4003 under the cap, 4005 with the sibling

        def op(n):
            self._read(self._nested(4, name, inner="<b>x</b>" * n))

        _linear(op, 2_500, 10_000)


class TestWordNetDepthCalibrated:
    """_MAX_HYPERNYM_DEPTH 256 against a real maximum chain of 19 (rock_hind.n.01,
    20 nodes) in wordnet, wordnet2021, wordnet2022, wordnet31 and english_wordnet."""

    def test_real_maximum_chain_walks(self):
        from nltk.test.unit.security_probes.ghsa_53pg_5qp8_mhvr import (
            WALKERS,
            _chain,
            _node_class,
        )

        leaf = _chain(_node_class(), 19)
        for walker in WALKERS:
            getattr(leaf, walker)()  # no refusal
        assert leaf.max_depth() == 19 and len(leaf.hypernym_paths()[0]) == 20

    def test_real_corpus_deepest_synset(self):
        import nltk.data
        from nltk.corpus.reader.wordnet import WordNetCorpusReader

        for name in (
            "wordnet",
            "wordnet2022",
            "wordnet2021",
            "wordnet31",
            "english_wordnet",
        ):
            try:
                root = nltk.data.find("corpora/" + name)
            except LookupError:
                continue
            wn = WordNetCorpusReader(root, None)
            ss = wn.synset("rock_hind.n.01")
            assert ss.max_depth() == 19
            assert max(len(p) for p in ss.hypernym_paths()) == 20
            assert max(d for _, d in ss.hypernym_distances()) == 19
            return
        pytest.skip("no WordNet corpus downloaded")


class TestSteppingParserCalibrated:
    """The 5 s stepping deadline against the real inputs: the demo grammar and
    the rdparser app's sentence parse in ~0.05 s with the same trees as the
    plain parser."""

    def test_real_inputs_parse_well_inside_the_deadline(self):
        from nltk import CFG
        from nltk.parse import RecursiveDescentParser, SteppingRecursiveDescentParser

        grammar = CFG.fromstring(
            """
            S -> NP VP
            NP -> Det N | Det N PP
            VP -> V NP | V NP PP
            PP -> P NP
            NP -> 'I'
            N -> 'man' | 'park' | 'telescope' | 'dog'
            Det -> 'the' | 'a'
            P -> 'in' | 'with'
            V -> 'saw'
            """
        )
        for sent in ("I saw a man in the park", "the dog saw a man in the park"):
            toks = sent.split()
            stepping = lambda: list(SteppingRecursiveDescentParser(grammar).parse(toks))
            trees = stepping()
            assert trees == list(RecursiveDescentParser(grammar).parse(toks))
            assert len(trees) == 2
            assert timing.charged(stepping) < 1.0  # ~0.05 s against a 5 s deadline


class TestRedosGroupCountCalibrated:
    """MAX_GROUP_COUNT 1000 against a real maximum of 9 capturing groups (the
    IEER document pattern in nltk.chunk.util) across every pattern NLTK ships."""

    def test_real_maximum_and_the_bound(self):
        from nltk.chunk.util import _IEER_DOC_RE

        assert _IEER_DOC_RE.groups == 9
        assert redos.compile("()" * redos.MAX_GROUP_COUNT).groups == 1000
        with pytest.raises(ValueError, match="MAX_GROUP_COUNT|capturing groups"):
            redos.compile("()" * (redos.MAX_GROUP_COUNT + 1))
        with pytest.raises(ValueError):
            redos.compile("()" * 50_000)
