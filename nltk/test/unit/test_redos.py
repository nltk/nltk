"""
Regression tests for the ReDoS backstop (GHSA-w3v8-gmh9-3wv7 umbrella).

Every NLTK sink that compiles a *caller-supplied* regular expression or tag
pattern must bound the match with a wall-clock timeout, so a crafted pattern
cannot pin a CPU core forever (catastrophic backtracking / ReDoS, CWE-1333).

The exploit patterns below are the ones actually reproduced against the
unpatched code:

* ``(a+)+$``  -- nested quantifier over the *same* sub-expression. The ``regex``
  engine's optimiser collapses this to linear time, so it must finish fast and
  *not* raise. Kept here so a future engine/opt regression is caught.
* ``(a|a)*$`` -- alternation of *identical* branches. Neither ``re`` nor the
  ``regex`` optimiser defuses this, so only the wall-clock timeout saves us. It
  must raise :class:`TimeoutError`. This is the case the timeout exists for.

Each sink is checked twice: a benign pattern still returns the right answer, and
the ``(a|a)*$`` exploit raises ``TimeoutError`` instead of hanging. The timeout
is monkeypatched short so the suite stays fast; the payload length is chosen so
the backtracking cannot possibly finish inside any small window.
"""

import time

import pytest

from nltk import redos

# A short bound keeps the exploit tests fast. The payloads below need ~2**N
# steps, so no benign-length window lets them finish -- the timeout always wins.
FAST_TIMEOUT = 0.5

#: Payload for the identical-branch exploit: long enough that 2**N steps cannot
#: complete inside FAST_TIMEOUT on any machine.
EVIL = "a" * 64 + "!"

DEFUSED = r"(a+)+$"  # engine linearises this -> must be fast, must NOT time out
BACKSTOP = r"(a|a)*$"  # engine cannot linearise -> only the timeout saves us


@pytest.fixture
def fast_timeout(monkeypatch):
    """Shorten the shared default so exploit cases resolve quickly."""
    monkeypatch.setattr(redos, "DEFAULT_TIMEOUT", FAST_TIMEOUT)
    return FAST_TIMEOUT


# --------------------------------------------------------------------------
# redos module itself
# --------------------------------------------------------------------------


class TestRedosModule:
    def test_default_timeout_is_tight(self):
        # Guard against re-introducing a 60s-style DoS amplifier: the busy-wait
        # window is itself the damage, so the default must stay small.
        assert redos.DEFAULT_TIMEOUT is not None
        assert 0 < redos.DEFAULT_TIMEOUT <= 10

    def test_functional_parity(self):
        assert redos.compile(r"\w+").findall("hi there") == ["hi", "there"]
        assert redos.compile(r"\s+").split("a b  c") == ["a", "b", "c"]
        assert redos.compile(r"a").sub("X", "banana") == "bXnXnX"
        assert [m.group() for m in redos.compile(r"\w+").finditer("ab cd")] == [
            "ab",
            "cd",
        ]

    def test_attribute_delegation(self):
        rx = redos.compile(r"(?P<w>\w+)")
        assert rx.pattern == r"(?P<w>\w+)"
        assert rx.groupindex.get("w") == 1  # delegated to the wrapped pattern

    def test_precompiled_and_timedpattern_inputs(self):
        import regex

        inner = regex.compile(r"\d+")
        assert redos.compile(inner).findall("a1b22") == ["1", "22"]
        tp = redos.compile(r"\d+")
        assert redos.compile(tp) is tp  # idempotent when no new timeout

    def test_engine_defuses_nested_quantifier(self, fast_timeout):
        # (a+)+$ must be linearised by the engine and finish well under the
        # (short) timeout -- i.e. NOT raise.
        start = time.perf_counter()
        assert redos.compile(DEFUSED).findall(EVIL) == []
        assert time.perf_counter() - start < FAST_TIMEOUT

    @pytest.mark.parametrize("op", ["findall", "search", "split", "finditer", "sub"])
    def test_backstop_fires_on_identical_branches(self, op, fast_timeout):
        rx = redos.compile(BACKSTOP)
        with pytest.raises(TimeoutError):
            if op == "finditer":
                list(rx.finditer(EVIL))
            elif op == "sub":
                rx.sub("x", EVIL)
            else:
                getattr(rx, op)(EVIL)

    def test_timeout_none_disables(self):
        # A trusted pattern may opt out; a benign match still works.
        assert redos.compile(r"\w+").search("hello", timeout=None).group() == "hello"


# --------------------------------------------------------------------------
# Sink: RegexpTokenizer / regexp_tokenize / regexp_span_tokenize
# --------------------------------------------------------------------------


class TestRegexpTokenizerReDoS:
    def test_benign(self):
        from nltk.tokenize import RegexpTokenizer, regexp_tokenize

        assert RegexpTokenizer(r"\w+").tokenize("Good muffins") == ["Good", "muffins"]
        assert RegexpTokenizer(r"\s+", gaps=True).tokenize("a b  c") == ["a", "b", "c"]
        assert list(RegexpTokenizer(r"\w+").span_tokenize("ab cd")) == [(0, 2), (3, 5)]
        assert regexp_tokenize("a b", r"\w+") == ["a", "b"]

    def test_tokenize_findall_exploit(self, fast_timeout):
        from nltk.tokenize import RegexpTokenizer

        with pytest.raises(TimeoutError):
            RegexpTokenizer(BACKSTOP).tokenize(EVIL)

    def test_span_tokenize_tokens_exploit(self, fast_timeout):
        from nltk.tokenize import RegexpTokenizer

        with pytest.raises(TimeoutError):
            list(RegexpTokenizer(BACKSTOP).span_tokenize(EVIL))

    def test_span_tokenize_gaps_exploit(self, fast_timeout):
        # Exercises regexp_span_tokenize() in nltk/tokenize/util.py.
        from nltk.tokenize import RegexpTokenizer

        with pytest.raises(TimeoutError):
            list(RegexpTokenizer(BACKSTOP, gaps=True).span_tokenize(EVIL))

    def test_regexp_tokenize_function_exploit(self, fast_timeout):
        from nltk.tokenize import regexp_tokenize

        with pytest.raises(TimeoutError):
            regexp_tokenize(EVIL, BACKSTOP)

    def test_regexp_span_tokenize_string_pattern_exploit(self, fast_timeout):
        # A bare string separator pattern is compiled through redos too.
        from nltk.tokenize.util import regexp_span_tokenize

        with pytest.raises(TimeoutError):
            list(regexp_span_tokenize(EVIL, BACKSTOP))


# --------------------------------------------------------------------------
# Sink: RegexpTagger
# --------------------------------------------------------------------------


class TestRegexpTaggerReDoS:
    def test_benign(self):
        from nltk.tag import RegexpTagger

        tagger = RegexpTagger([(r".*ing$", "VBG"), (r".*", "NN")])
        assert tagger.tag(["walking", "dog"]) == [("walking", "VBG"), ("dog", "NN")]

    def test_json_roundtrip_still_works(self):
        from nltk.tag import RegexpTagger

        tagger = RegexpTagger([(r".*ing$", "VBG")])
        regexps, _ = tagger.encode_json_obj()
        assert regexps == [(r".*ing$", "VBG")]
        # decode re-compiles through redos and still tags correctly.
        rebuilt = RegexpTagger.decode_json_obj((regexps, None))
        assert rebuilt.tag(["walking"]) == [("walking", "VBG")]

    def test_exploit(self, fast_timeout):
        from nltk.tag import RegexpTagger

        tagger = RegexpTagger([(BACKSTOP, "X"), (r".*", "NN")])
        with pytest.raises(TimeoutError):
            tagger.tag([EVIL])


# --------------------------------------------------------------------------
# Sink: chunk rules (ChunkRule / RegexpChunkParser)
# --------------------------------------------------------------------------


class TestChunkReDoS:
    def test_benign(self):
        from nltk.chunk.regexp import ChunkRule, RegexpChunkParser

        parser = RegexpChunkParser(
            [ChunkRule("<DT><NN>", "np")], chunk_label="NP"
        )
        tree = parser.parse([("the", "DT"), ("dog", "NN")])
        assert "NP" in str(tree)

    def test_hostile_tag_pattern_passes_validator_but_is_bounded(self, fast_timeout):
        # The payload deliberately passes CHUNK_TAG_PATTERN (the earlier huntr
        # fix): '|' and '*' are allowed, so the validator is NOT the defence --
        # the timeout is.
        from nltk.chunk.regexp import ChunkRule, RegexpChunkParser

        parser = RegexpChunkParser([ChunkRule("<a|a>*<b>", "x")], chunk_label="NP")
        with pytest.raises(TimeoutError):
            parser.parse([("a", "a")] * 64)

    def test_raw_regexpchunkrule_exploit(self, fast_timeout):
        # RegexpChunkRule takes a *raw* regex (no tag-pattern restriction).
        from nltk.chunk.regexp import ChunkString, RegexpChunkRule

        rule = RegexpChunkRule(BACKSTOP, r"\g<0>", "raw")
        cs = ChunkString.__new__(ChunkString)
        cs._str = EVIL
        cs._debug = 0
        with pytest.raises(TimeoutError):
            rule.apply(cs)

    def test_dead_redos_shaped_attrs_removed(self):
        # Task #9: the unused, ReDoS-shaped _CHUNK/_STRIP class attributes are gone.
        from nltk.chunk.regexp import ChunkString

        assert not hasattr(ChunkString, "_CHUNK")
        assert not hasattr(ChunkString, "_STRIP")


# --------------------------------------------------------------------------
# Sink: tgrep /regex/ node literal
# --------------------------------------------------------------------------


class TestTgrepReDoS:
    def test_benign(self):
        pytest.importorskip("pyparsing")
        from nltk import tgrep
        from nltk.tree import ParentedTree

        tree = ParentedTree.fromstring("(S (NP (DT the) (NN dog)))")
        matcher = tgrep.tgrep_compile("/NN/")
        assert list(tgrep.tgrep_positions(matcher, [tree]))  # finds the NN node

    def test_exploit(self, fast_timeout):
        pytest.importorskip("pyparsing")
        from nltk import tgrep
        from nltk.tree import ParentedTree

        tree = ParentedTree.fromstring("(S (X %s))" % EVIL)
        matcher = tgrep.tgrep_compile("/(a|a)*$/")
        with pytest.raises(TimeoutError):
            list(tgrep.tgrep_positions(matcher, [tree]))


# --------------------------------------------------------------------------
# Sink: Text.findall / TokenSearcher (rrv8) -- reaffirm + shared tight default
# --------------------------------------------------------------------------


class TestTokenSearcherReDoS:
    def test_shared_tight_default(self):
        import nltk.text as text_mod

        assert text_mod.TOKENSEARCH_TIMEOUT == redos.DEFAULT_TIMEOUT

    def test_benign(self):
        from nltk.text import TokenSearcher

        searcher = TokenSearcher(["the", "dog", "sat"])
        assert searcher.findall("<the><dog>") == [["the", "dog"]]

    def test_exploit(self):
        # The token delimiters make each ``<tok>`` fixed-width, so the classic
        # cross-token catastrophe is defused; the real blow-up lives *inside* a
        # single long, attacker-controlled corpus token matched against a
        # quantified-alternation query.
        from nltk.text import TokenSearcher

        searcher = TokenSearcher(["a" * 64])
        with pytest.raises(TimeoutError):
            searcher.findall("<(a|a)*b>", timeout=FAST_TIMEOUT)
