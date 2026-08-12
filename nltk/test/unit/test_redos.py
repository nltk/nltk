"""
Regression tests for the ReDoS backstop (GHSA-w3v8-gmh9-3wv7 umbrella).

Every NLTK sink that compiles a *caller-supplied* regular expression or tag
pattern must bound the match with a wall-clock timeout, so a crafted pattern
cannot pin a CPU core forever (catastrophic backtracking / ReDoS, CWE-1333).

This file bakes the full adversarial *attack sweep* into CI. Each hardened sink
is hammered with a battery of catastrophic-backtracking patterns; every one must
raise :class:`TimeoutError` (the timeout fired) rather than hang. The sweep was
first run out-of-process against the unpatched code, where every pattern below
ran to a hard wall-clock kill -- so these are proven exploits, not hypotheticals.

Two pattern families, empirically separated:

* ``BACKSTOP_FAMILY`` -- alternation of identical/overlapping branches
  (``(a|a)*`` and friends). Neither ``re`` nor the ``regex`` optimiser defuses
  these, so ONLY the wall-clock timeout stops them. They must raise.
* ``DEFUSED_FAMILY`` -- nested quantifiers over the *same* sub-expression
  (``(a+)+$`` etc.). The ``regex`` optimiser linearises these outright, so they
  must finish fast and must NOT raise. Kept so a future engine/opt regression
  (which would turn them back into hangs the timeout must then catch) is visible.

The timeout is monkeypatched short so the suite stays fast; payloads are long
enough that 2**N backtracking cannot finish inside any small window.
"""

import time

import pytest

from nltk import redos

FAST_TIMEOUT = 0.5
EVIL = "a" * 64 + "!"  # long enough that no small window lets 2**N finish

#: Raw-regex exploits the engine does NOT defuse -> the timeout MUST fire.
BACKSTOP_FAMILY = [
    r"(a|a)*$",  # identical single-char branches
    r"(a|a|a)*$",  # three identical branches
    r"(aa|aa)*$",  # identical multi-char branches
    r"([ab]|[ab])*$",  # identical character-class branches
]

#: Exploits the ``regex`` optimiser linearises -> must finish fast, must NOT raise.
DEFUSED_FAMILY = [
    r"(a+)+$",
    r"(a*)*$",
    r"((a*)*)*$",
    r"([a-z]+)*$",
]

#: Chunk *tag patterns* that pass CHUNK_TAG_PATTERN yet derive a backtracking
#: regex the engine cannot defuse -> the timeout MUST fire.
CHUNK_BACKSTOP_FAMILY = [
    "<a|a>*<b>",
    "<a|a|a>*<b>",
    "<a|a>+<b>",
]

DEFUSED = DEFUSED_FAMILY[0]
BACKSTOP = BACKSTOP_FAMILY[0]


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

    @pytest.mark.parametrize("pattern", DEFUSED_FAMILY)
    def test_engine_defuses_nested_quantifier(self, pattern, fast_timeout):
        # These must be linearised by the engine and finish well under the
        # (short) timeout -- i.e. NOT raise (the exact match content is
        # irrelevant; some, e.g. ``(a*)*$``, legitimately match the empty
        # string at end-of-input).
        start = time.perf_counter()
        redos.compile(pattern).findall(EVIL)
        assert time.perf_counter() - start < FAST_TIMEOUT

    @pytest.mark.parametrize("pattern", BACKSTOP_FAMILY)
    @pytest.mark.parametrize("op", ["findall", "search", "split", "finditer", "sub"])
    def test_backstop_fires_on_identical_branches(self, op, pattern, fast_timeout):
        rx = redos.compile(pattern)
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

    @pytest.mark.parametrize("pattern", BACKSTOP_FAMILY)
    def test_tokenize_findall_exploit(self, pattern, fast_timeout):
        from nltk.tokenize import RegexpTokenizer

        with pytest.raises(TimeoutError):
            RegexpTokenizer(pattern).tokenize(EVIL)

    @pytest.mark.parametrize("pattern", BACKSTOP_FAMILY)
    def test_span_tokenize_tokens_exploit(self, pattern, fast_timeout):
        from nltk.tokenize import RegexpTokenizer

        with pytest.raises(TimeoutError):
            list(RegexpTokenizer(pattern).span_tokenize(EVIL))

    @pytest.mark.parametrize("pattern", BACKSTOP_FAMILY)
    def test_span_tokenize_gaps_exploit(self, pattern, fast_timeout):
        # Exercises regexp_span_tokenize() in nltk/tokenize/util.py.
        from nltk.tokenize import RegexpTokenizer

        with pytest.raises(TimeoutError):
            list(RegexpTokenizer(pattern, gaps=True).span_tokenize(EVIL))

    @pytest.mark.parametrize("pattern", BACKSTOP_FAMILY)
    def test_regexp_tokenize_function_exploit(self, pattern, fast_timeout):
        from nltk.tokenize import regexp_tokenize

        with pytest.raises(TimeoutError):
            regexp_tokenize(EVIL, pattern)

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

    @pytest.mark.parametrize("pattern", BACKSTOP_FAMILY)
    def test_exploit(self, pattern, fast_timeout):
        from nltk.tag import RegexpTagger

        tagger = RegexpTagger([(pattern, "X"), (r".*", "NN")])
        with pytest.raises(TimeoutError):
            tagger.tag([EVIL])


# --------------------------------------------------------------------------
# Sink: chunk rules (every rule type funnels through RegexpChunkRule)
# --------------------------------------------------------------------------


class TestChunkReDoS:
    def test_benign(self):
        from nltk.chunk.regexp import ChunkRule, RegexpChunkParser

        parser = RegexpChunkParser([ChunkRule("<DT><NN>", "np")], chunk_label="NP")
        tree = parser.parse([("the", "DT"), ("dog", "NN")])
        assert "NP" in str(tree)

    @pytest.mark.parametrize("tag_pattern", CHUNK_BACKSTOP_FAMILY)
    def test_hostile_tag_pattern_passes_validator_but_is_bounded(
        self, tag_pattern, fast_timeout
    ):
        # These deliberately pass CHUNK_TAG_PATTERN (the earlier huntr fix):
        # '|' and '*'/'+' are allowed, so the validator is NOT the defence --
        # the timeout is.
        from nltk.chunk.regexp import ChunkRule, RegexpChunkParser

        parser = RegexpChunkParser([ChunkRule(tag_pattern, "x")], chunk_label="NP")
        with pytest.raises(TimeoutError):
            parser.parse([("a", "a")] * 64)

    @pytest.mark.parametrize(
        "make_rule",
        [
            pytest.param(lambda C: C.ChunkRule("<a|a>*<b>", "d"), id="ChunkRule"),
            pytest.param(lambda C: C.StripRule("<a|a>*<b>", "d"), id="StripRule"),
            pytest.param(lambda C: C.UnChunkRule("<a|a>*<b>", "d"), id="UnChunkRule"),
            pytest.param(
                lambda C: C.MergeRule("<a|a>*<b>", "<c>", "d"), id="MergeRule"
            ),
            pytest.param(
                lambda C: C.SplitRule("<a|a>*<b>", "<c>", "d"), id="SplitRule"
            ),
            pytest.param(
                lambda C: C.ChunkRuleWithContext("", "<a|a>*<b>", "", "d"),
                id="ChunkRuleWithContext",
            ),
        ],
    )
    def test_every_rule_type_is_bounded(self, make_rule, fast_timeout):
        # Every RegexpChunkRule subclass must route its (caller-derived) regex
        # through the redos choke point and be bounded on application.
        import nltk.chunk.regexp as C

        rule = make_rule(C)
        assert isinstance(rule._regexp, redos.TimedPattern)  # choke point wrapped it
        cs = C.ChunkString.__new__(C.ChunkString)
        cs._str = "{" + "<a>" * 64 + "}"
        cs._debug = 0
        with pytest.raises(TimeoutError):
            rule.apply(cs)

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

    @pytest.mark.parametrize("pattern", BACKSTOP_FAMILY)
    def test_exploit(self, pattern, fast_timeout):
        pytest.importorskip("pyparsing")
        from nltk import tgrep
        from nltk.tree import ParentedTree

        tree = ParentedTree.fromstring(f"(S (X {EVIL}))")
        matcher = tgrep.tgrep_compile(f"/{pattern}/")
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

    @pytest.mark.parametrize("inner", ["(a|a)*", "(a|a|a)*", "([ab]|[ab])*"])
    def test_exploit(self, inner):
        # Token delimiters make each ``<tok>`` fixed-width, so the cross-token
        # catastrophe is defused; the real blow-up is *inside* a single long,
        # attacker-controlled corpus token matched against a quantified query.
        from nltk.text import TokenSearcher

        searcher = TokenSearcher(["a" * 64])
        with pytest.raises(TimeoutError):
            searcher.findall(f"<{inner}b>", timeout=FAST_TIMEOUT)


# --------------------------------------------------------------------------
# Sink: Chat(pairs) -- caller/author regex matched against unbounded user input
# --------------------------------------------------------------------------


class TestChatReDoS:
    def test_benign(self):
        from nltk.chat.util import Chat, reflections

        bot = Chat([(r"hello (.*)", ["hi %1"])], reflections)
        assert bot.respond("hello world") == "hi world"

    def test_pattern_compiled_through_redos(self):
        # Structural guard: every pair pattern goes through redos (engine +
        # timeout). Fails FAST and cleanly if the wiring is ever reverted to
        # stdlib ``re`` -- rather than hanging the suite.
        from nltk.chat.util import Chat, reflections

        bot = Chat([(r"(a|a)*z", ["x"])], reflections)
        assert isinstance(bot._pairs[0][0], redos.TimedPattern)

    def test_exploit_is_bounded(self, fast_timeout):
        # ``(a|a)*z`` against a long input is a hard hang on stdlib ``re``.
        # Through redos it is bounded: the ``regex`` engine linearises this
        # anchored ``match`` outright (so it usually returns fast), and the
        # wall-clock timeout backstops anything it cannot. Either way: no hang.
        from nltk.chat.util import Chat, reflections

        bot = Chat([(r"(a|a)*z", ["x"])], reflections)
        start = time.perf_counter()
        try:
            bot.respond("a" * 64)
        except TimeoutError:
            pass
        assert time.perf_counter() - start < 2.0


# --------------------------------------------------------------------------
# Sink: Tree.fromstring(node_pattern=, leaf_pattern=) -- caller regex over text
# --------------------------------------------------------------------------


class TestTreeFromstringReDoS:
    def test_benign_default(self):
        from nltk.tree import Tree

        tree = Tree.fromstring("(S (NP the dog) (VP ran))")
        assert tree.label() == "S" and len(tree) == 2

    def test_benign_custom_pattern(self):
        from nltk.tree import Tree

        tree = Tree.fromstring("(S (NP dog))", node_pattern=r"\w+", leaf_pattern=r"\w+")
        assert tree.label() == "S"

    @pytest.mark.parametrize("kw", ["leaf_pattern", "node_pattern"])
    def test_caller_pattern_exploit(self, kw, fast_timeout):
        # A caller-supplied node/leaf pattern is run over the (unbounded) tree
        # string via finditer, where the engine cannot defuse a forced-failure
        # identical-branch pattern -- the timeout must fire.
        from nltk.tree import Tree

        s = ("(" if kw == "node_pattern" else "") + "a" * 64
        with pytest.raises(TimeoutError):
            Tree.fromstring(s, **{kw: r"(a|a)*z"})
