# Natural Language Toolkit: expanded attack harness for the CCG lexicon parser
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The CCG lexicon parser (nltk.ccg.lexicon) driven with hostile and benign
input and judged by what the real parser does: the GHSA-89p3-fcch-88ph shape
(a flat application chain, quadratic before the cursor rewrite) at the probe's
own sizes, the bracketed and nested shapes the same tail re-slicing made
quadratic, the MAX_PARSE_LEN and MAX_PARSE_DEPTH refusals, malformed and
hostile characters, every regex the module compiles fed its worst case, the
primitive and family tables, the lexicons the documentation parses, and the
chart parser running on them exactly as documented. Nothing is mocked and no
guard is patched; every timing goes through nltk.test.unit.timing.
"""

import ast
import contextlib
import doctest
import io
import pathlib
import random
import re
import string
from collections import defaultdict

import pytest

import nltk.test
from nltk import redos
from nltk.ccg import chart
from nltk.ccg import lexicon as ccglex
from nltk.ccg.api import CCGVar, Direction, FunctionalCategory, PrimitiveCategory
from nltk.ccg.lexicon import (
    MAX_PARSE_DEPTH,
    MAX_PARSE_LEN,
    CCGLexicon,
    Token,
    augParseCategory,
    fromstring,
    matchBrackets,
    nextCategory,
)
from nltk.sem.logic import Expression, LogicalExpressionException
from nltk.termsec import sanitize_terminal
from nltk.test.unit import timing
from nltk.test.unit.security_probes.ghsa_89p3_fcch_88ph import (
    FLAT_BIG,
    FLAT_ENTRIES,
    FLAT_SMALL,
    flat_lexicon,
)
from nltk.tree import Tree

NUL = chr(0)
BEL = chr(7)
ESC = chr(0x1B)
CSI = chr(0x9B)
DEL = chr(0x7F)
RLO = chr(0x202E)
LONE_SURROGATE = chr(0xDCFF)
# Every boundary str.splitlines breaks a lexicon at
LINE_BREAKS = [
    chr(c) for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85, 0x2028, 0x2029)
]


def _chain(n, operator="/S"):
    """A lexicon whose one entry is a flat chain of ``n`` applications."""
    return ":- S\nw => S" + operator * n + "\n"


def _mixed_chain(n):
    """A flat chain cycling through every slash and modality spelling."""
    operators = ("/S", "\\S", "/.S", "\\,S", "/_S", "\\_,S", "/,.S")
    return ":- S\nw => S" + "".join(operators[i % 7] for i in range(n)) + "\n"


def _applications(cat):
    """How many applications a left-nested category carries, iteratively
    (its own __str__ recurses, which a 1000-deep chain cannot afford)."""
    count = 0
    while isinstance(cat, FunctionalCategory):
        cat = cat.res()
        count += 1
    return count


def _name(i):
    """A letters-only name for item ``i`` (PRIM_RE accepts no digits)."""
    out = ""
    while True:
        out = string.ascii_uppercase[i % 26] + out
        i //= 26
        if i == 0:
            return "p" + out


def _primitive_table(n):
    """``n`` primitives on one line and ``n`` entries naming the last one."""
    last = _name(n - 1)
    head = ":- S, " + ", ".join(_name(i) for i in range(n)) + "\n"
    return head + "".join(f"w{_name(i)} => {last}\n" for i in range(n))


def _primitive_lines(n):
    """``n`` separate ``:-`` lines before one entry."""
    return ":- S\n" * n + "w => S\n"


def _entries(n):
    """``n`` word entries over one primitive."""
    return ":- S\n" + "".join("w%s => S/S\n" % _name(i) for i in range(n))


def _derivation(lex, sentence):
    """Every parse of ``sentence`` and what printCCGDerivation writes for the
    first one, through the real print path (safe_print)."""
    parser = chart.CCGChartParser(lex, chart.DefaultRuleSet)
    parses = list(parser.parse(sentence.split()))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        chart.printCCGDerivation(parses[0])
    return parses, out.getvalue()


def _rows(text):
    """A derivation with its alignment folded: a rule line becomes
    ``(hyphens, mark)``, any other line its single-spaced text."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            mark = line.lstrip("-")
            rows.append((len(line) - len(mark), mark))
        else:
            rows.append(" ".join(line.split()))
    return rows


# ==========================================================================
# GHSA-89p3-fcch-88ph: the flat application chain
# ==========================================================================


class TestFlatChainScaling:
    def test_probe_shape_at_the_probe_sizes_is_linear(self):
        # The lexicon and sizes the probe measures, through the same helper:
        # the cursor parser reads ~4x, the tail re-slicer it replaced 11x to 15x
        ratio = timing.scaling_ratio(
            lambda n: fromstring(flat_lexicon(n)),
            FLAT_SMALL,
            FLAT_BIG,
            cpu_bound=True,
        )
        assert ratio < timing.QUADRATIC_RATIO, ratio

    def test_probe_shape_is_a_real_parse(self):
        lex = fromstring(flat_lexicon(FLAT_BIG))
        assert len(lex._entries) == FLAT_ENTRIES
        for word in lex._entries:
            assert _applications(lex.categories(word)[0].categ()) == FLAT_BIG

    def test_backward_and_modal_operators_are_linear(self):
        timing.assert_subquadratic(
            lambda n: fromstring(_mixed_chain(n)), 5_000, 20_000, cpu_bound=True
        )
        cat = fromstring(_mixed_chain(7)).categories("w")[0].categ()
        assert str(cat) == "(((((((S/S)\\S)/.S)\\,S)/_S)\\_,S)/,.S)"


class TestBracketScaling:
    # matchBrackets re-sliced its tail one character at a time pre-fix, so a
    # bracketed chain, sibling groups and nests were quadratic as well
    def test_bracketed_chain_is_linear(self):
        timing.assert_subquadratic(
            lambda n: fromstring(":- S\nw => (S" + "/S" * n + ")\n"),
            10_000,
            40_000,
            cpu_bound=True,
        )

    def test_sibling_groups_are_linear(self):
        timing.assert_subquadratic(
            lambda n: fromstring(":- S\nw => " + "/".join(["(S/S)"] * n) + "\n"),
            2_500,
            10_000,
            cpu_bound=True,
        )

    def test_nested_groups_in_a_chain_are_linear(self):
        unit = "(" * 50 + "S" + ")" * 50
        timing.assert_subquadratic(
            lambda n: fromstring(":- S\nw => " + "/".join([unit] * n) + "\n"),
            200,
            800,
            cpu_bound=True,
        )


# ==========================================================================
# MAX_PARSE_LEN and MAX_PARSE_DEPTH
# ==========================================================================


class TestLengthCap:
    def test_exact_cap_parses_and_one_more_is_refused(self):
        exact = "SS" + "/S" * ((MAX_PARSE_LEN - 2) // 2)
        assert len(exact) == MAX_PARSE_LEN
        cat, _ = augParseCategory(exact, ["S", "SS"], {})
        assert _applications(cat) == (MAX_PARSE_LEN - 2) // 2
        with pytest.raises(ValueError, match="nltk.ccg.lexicon.MAX_PARSE_LEN"):
            augParseCategory("S" + exact, ["S", "SS", "SSS"], {})

    def test_over_cap_is_refused_before_it_is_walked(self):
        # ten times the cap: a length check, not a parse, inside the budget
        line = _chain(5 * MAX_PARSE_LEN)
        with timing.budget(2.0, "refusing a 1 MB category", cpu_bound=True):
            with pytest.raises(ValueError, match="MAX_PARSE_LEN"):
                fromstring(line)

    def test_bracket_scanner_honours_the_cap_from_its_cursor(self):
        over = "(" + "S" * MAX_PARSE_LEN + ")"
        with pytest.raises(ValueError, match="MAX_PARSE_LEN"):
            matchBrackets(over)
        with pytest.raises(ValueError, match="MAX_PARSE_LEN"):
            nextCategory(over)
        # the cap bounds the remainder after the cursor, not the whole string
        prefix = "x" * MAX_PARSE_LEN
        assert matchBrackets(prefix + "(S)", MAX_PARSE_LEN) == (
            "(S)",
            MAX_PARSE_LEN + 3,
        )


class TestDepthAndBrackets:
    def test_nesting_under_the_depth_cap_parses(self):
        depth = MAX_PARSE_DEPTH - 100
        cat, _ = augParseCategory("(" * depth + "S" + ")" * depth, ["S"], {})
        assert str(cat) == "S"

    @pytest.mark.parametrize(
        "shape",
        [
            "(" * (MAX_PARSE_DEPTH + 1) + "S" + ")" * (MAX_PARSE_DEPTH + 1),
            "S" + "/(S" * (MAX_PARSE_DEPTH + 1) + ")" * (MAX_PARSE_DEPTH + 1),
            "(" * (MAX_PARSE_DEPTH + 100) + "S",  # deep and never closed
        ],
        ids=["nest", "right-nested chain", "unclosed nest"],
    )
    def test_nesting_over_the_depth_cap_is_refused(self, shape):
        with pytest.raises(ValueError, match="nltk.ccg.lexicon.MAX_PARSE_DEPTH"):
            augParseCategory(shape, ["S"], {})

    @pytest.mark.parametrize(
        "shape, exc",
        [
            ("(S/S", AssertionError),
            ("(", AssertionError),
            ("S/S)", AttributeError),
            (")", AttributeError),
            ("()", AttributeError),
            ("", AttributeError),
            ("S/", AttributeError),
            ("S//S", AttributeError),
            ("S[", AttributeError),
            ("S[]", AttributeError),
            ("S[1]", AttributeError),
            ("S1", AttributeError),
            ("S S", AttributeError),
        ],
    )
    def test_malformed_category_raises_and_returns(self, shape, exc):
        with timing.budget(1.0, "a malformed category", cpu_bound=True):
            with pytest.raises(exc):
                augParseCategory(shape, ["S"], {})

    def test_unmatched_bracket_names_the_tail_from_the_cursor(self):
        with pytest.raises(AssertionError, match=r"Unmatched bracket in string '\(S'"):
            matchBrackets("N/(S", 2)

    def test_cursor_api(self):
        assert matchBrackets("(S/N)/N") == ("(S/N)", 5)
        assert matchBrackets("N/(S/N)/N", 2) == ("(S/N)", 7)
        assert nextCategory("S/N") == ("S", 1)
        assert nextCategory("N/(S)", 2) == ("(S)", 5)
        assert nextCategory("S[sg,x]/N") == ("S[sg,x]", 7)
        with pytest.raises(AttributeError):
            nextCategory("/N")


# ==========================================================================
# Hostile characters in tokens, categories and comments
# ==========================================================================


class TestHostileCharacters:
    def test_every_line_break_splits_entries(self):
        text = ":- S" + "".join(
            sep + _name(i) + " => S" for i, sep in enumerate(LINE_BREAKS)
        )
        lex = fromstring(text + "\r\n")
        assert sorted(lex._entries) == sorted(_name(i) for i in range(len(LINE_BREAKS)))

    @pytest.mark.parametrize(
        "hostile",
        [NUL, ESC + "[31m", CSI + "31m", RLO, BEL, DEL, LONE_SURROGATE],
        ids=["NUL", "ESC", "CSI", "RLO", "BEL", "DEL", "surrogate"],
    )
    def test_hostile_characters_in_a_token_are_kept_verbatim(self, hostile):
        token = hostile + "w"
        lex = fromstring(":- S\n" + token + " => S\n")
        assert list(lex._entries) == [token]
        assert [str(c) for c in lex.categories(token)] == ["S"]

    @pytest.mark.parametrize(
        "hostile", [NUL, ESC, RLO, " ", "\t"], ids=["NUL", "ESC", "RLO", "SP", "TAB"]
    )
    def test_hostile_characters_in_a_category_are_refused(self, hostile):
        with pytest.raises(AttributeError):
            fromstring(":- S\nw => S" + hostile + "S\n")

    def test_comments_absorb_hostile_characters(self):
        lex = fromstring(":- S\nw => S # " + NUL + ESC + "]0;x" + BEL + RLO + "\n")
        assert list(lex._entries) == ["w"]
        assert [str(c) for c in lex.categories("w")] == ["S"]

    def test_derivation_print_neutralises_escapes_and_bidi(self, capsys):
        red, rev = ESC + "[31mred", RLO + "rev"
        lex = fromstring(":- S, N\n" + red + " => N\n" + rev + " => S\\N\n")
        parser = chart.CCGChartParser(lex, chart.DefaultRuleSet)
        parses = list(parser.parse([red, rev]))
        assert parses
        chart.printCCGDerivation(parses[0])
        out = capsys.readouterr().out
        assert "red" in out and "rev" in out and _rows(out)[-1] == "S"
        assert ESC not in out and RLO not in out
        # the lexicon keeps the raw token; the terminal sanitiser removes it
        assert ESC in str(lex) and RLO in str(lex)
        clean = sanitize_terminal(str(lex))
        assert ESC not in clean and RLO not in clean

    def test_bytes_are_refused_and_undecodable_text_parses(self):
        with pytest.raises(TypeError):
            fromstring(b":- S\nw => S\n")
        raw = b":- S\n\xff\xfew => S\n".decode("utf-8", "surrogateescape")
        lex = fromstring(raw)
        (token,) = lex._entries
        assert token.encode("utf-8", "surrogateescape") == b"\xff\xfew"


# ==========================================================================
# Primitive, family and word forms
# ==========================================================================


class TestLexiconForms:
    def test_families_chain_and_the_last_definition_wins(self):
        lex = fromstring(":- S, N\nA :: S/N\nB :: A/N\nA :: S\\N\nw => B\nv => A\n")
        assert [str(c) for c in lex.categories("w")] == ["((S/N)/N)"]
        assert [str(c) for c in lex.categories("v")] == ["(S\\N)"]

    @pytest.mark.parametrize(
        "text",
        [
            ":- S, N\nDet :: Det/N\n",
            ":- S, N\nX :: Y/N\nY :: S\n",
            "w => S\n:- S\n",
            ":- S\nw => X\n",
            ":- S\nw => var[sg]\n",
        ],
        ids=["self-reference", "forward reference", "entry first", "unknown", "var[]"],
    )
    def test_unknown_names_are_refused(self, text):
        with pytest.raises(AssertionError, match="neither a family nor primitive"):
            fromstring(text)

    def test_primitive_lines_accumulate_in_order(self):
        lex = fromstring(":- S, N\n:- N, V\nw => V\n")
        assert lex._primitives == ["S", "N", "N", "V"]
        assert str(lex.start()) == "S"
        assert [str(c) for c in lex.categories("w")] == ["V"]

    def test_augParseCategory_accepts_any_container_of_primitives(self):
        for primitives in (["S", "N"], ("S", "N"), {"S", "N"}, frozenset({"S", "N"})):
            cat, _ = augParseCategory("S/N", primitives, {})
            assert str(cat) == "(S/N)"

    def test_variables_subscripts_and_modalities(self):
        lex = fromstring(
            ":- S, N\n"
            "and => var\\.,var/.,var\n"
            "w => S[sg]/N[pl,x]\n"
            "q => (S\\_N)/(S\\_N)\n"
        )
        assert [str(c) for c in lex.categories("and")] == ["((_var0\\.,_var0)/.,_var0)"]
        assert [str(c) for c in lex.categories("w")] == ["(S['sg']/N['pl','x'])"]
        assert [str(c) for c in lex.categories("q")] == ["((S\\_N)/(S\\_N))"]
        assert lex.categories("q")[0].categ().res().dir().is_variable()

    def test_compact_and_odd_identifiers(self):
        lex = fromstring(":- S\na=>S\nb/c => S\ne==>S\n")
        assert sorted(lex._entries) == ["a", "b/c", "e"]
        for text in (":- S\n:: S\n", ":- S\na S\n", ":- S\na => {x}\n"):
            with pytest.raises(AttributeError):
                fromstring(text)

    def test_empty_and_comment_only_input_has_no_start_category(self):
        for text in ("", "   \n", "# nothing\n\n"):
            with pytest.raises(IndexError):
                fromstring(text)

    def test_semantics_forms(self):
        lex = fromstring(":- S, NP\neat => S\\NP/NP {\\x y.eat(x,y)}\n", True)
        assert str(lex.categories("eat")[0]) == "((S\\NP)/NP) {\\x y.eat(x,y)}"
        with pytest.raises(AssertionError, match="must contain semantics"):
            fromstring(":- S\nw => S\n", True)
        with timing.budget(5.0, "hostile semantics", cpu_bound=True):
            with pytest.raises(LogicalExpressionException):
                fromstring(":- S\nw => S {(((}\n", True)
            # the logic parser's own depth cap, reached through the lexicon
            deep = "(" * 20_000 + "x" + ")" * 20_000
            with pytest.raises(LogicalExpressionException):
                fromstring(":- S\nw => S {" + deep + "}\n", True)
            fromstring(":- S\nw => S {" + "x" * 200_000 + "}\n", True)

    def test_parseLexicon_alias_still_parses(self):
        with pytest.warns(DeprecationWarning):
            lex = ccglex.parseLexicon(":- S\nw => S\n")
        assert [str(c) for c in lex.categories("w")] == ["S"]


# ==========================================================================
# Every regex the module compiles, fed its worst case
# ==========================================================================

_LINE = 200_000  # line-level regexes see no length cap
_CAT = MAX_PARSE_LEN - 10_000  # category-level ones run under the cap

# (label, lexicon line, outcome); the label is the test id. The payload must
# never become the id: pytest writes the node id to PYTEST_CURRENT_TEST and
# Windows refuses an environment variable over 32767 characters.
_REGEX_PAYLOADS = [
    ("LEX_RE ident then '=' run", "a" + "=" * _LINE, AttributeError),
    ("LEX_RE ident then '-' run", "a" + "-" * _LINE, AttributeError),
    ("LEX_RE 'a=' pairs", "a=" * _LINE, AttributeError),
    ("LEX_RE letters then spaces", "a" * _LINE + " " * _LINE, AttributeError),
    ("LEX_RE arrow without ident", " " * _LINE + "=> S", AttributeError),
    (
        "RHS_RE spaces then open brace",
        "w => S" + " " * _LINE + "{" + "x" * _LINE,
        "parsed",
    ),
    ("RHS_RE open braces", "w => S" + "{" * _LINE, "parsed"),
    ("RHS_RE close braces", "w => S" + "}" * _LINE, "parsed"),
    ("SEMANTICS_RE unclosed", "w => S {" + "x" * _LINE, "parsed"),
    ("COMMENTS_RE hash run", "w => S " + "#" * _LINE, "parsed"),
    ("PRIM_RE open subscripts", "w => S" + "[" * _CAT, AttributeError),
    (
        "PRIM_RE unclosed subscript list",
        "w => S[" + "a," * (_CAT // 2),
        AttributeError,
    ),
    ("NEXTPRIM_RE one long name", "w => " + "S" * _CAT, AssertionError),
    ("APP_RE slash run", "w => S" + "/" * _CAT, AttributeError),
    ("APP_RE slash-dot run", "w => S" + "/." * (_CAT // 2), AttributeError),
    (
        "APP_RE slash-modality run",
        "w => S" + "/_," * (_CAT // 3),
        AttributeError,
    ),
    ("brackets never closed", "w => " + "(" * _CAT, ValueError),
    ("brackets never opened", "w => S" + ")" * _CAT, AttributeError),
    ("empty bracket pairs", "w => " + "()" * (_CAT // 2), AttributeError),
    ("over-cap chain", "w => S" + "/S" * MAX_PARSE_LEN, ValueError),
]


class TestRegexPayloads:
    @pytest.mark.parametrize(
        "label, line, outcome",
        _REGEX_PAYLOADS,
        ids=[label for label, _, _ in _REGEX_PAYLOADS],
    )
    def test_payload_is_bounded(self, label, line, outcome):
        with timing.budget(2.0, label, cpu_bound=True):
            if outcome == "parsed":
                fromstring(":- S\n" + line + "\n")
            else:
                with pytest.raises(outcome):
                    fromstring(":- S\n" + line + "\n")


# ==========================================================================
# The primitive table (fixed here): a list scan per name was O(P*E)
# ==========================================================================


class TestPrimitiveTables:
    def test_lookup_of_the_last_primitive_is_linear(self):
        # P primitives, E entries naming the last: 10 s at 400 KB on the list
        timing.assert_subquadratic(
            lambda n: fromstring(_primitive_table(n)), 5_000, 20_000, cpu_bound=True
        )

    def test_many_primitive_lines_are_linear(self):
        # primitives = primitives + [...] rebuilt the list per ':-' line
        timing.assert_subquadratic(
            lambda n: fromstring(_primitive_lines(n)), 20_000, 80_000, cpu_bound=True
        )

    def test_many_entries_are_linear(self):
        timing.assert_subquadratic(
            lambda n: fromstring(_entries(n)), 2_500, 10_000, cpu_bound=True
        )
        lex = fromstring(_entries(5_000))
        assert len(lex._entries) == 5_000
        assert [str(c) for c in lex.categories("w" + _name(4_999))] == ["(S/S)"]


# ==========================================================================
# The documented lexicons, parsed and used exactly as documented
# ==========================================================================

# nltk/test/ccg.doctest, "Relative Clauses"
_RELATIVE_CLAUSES = """
    :- S, NP, N, VP

    Det :: NP/N
    Pro :: NP
    Modal :: S\\NP/VP

    TV :: VP/NP
    DTV :: TV/NP

    the => Det

    that => Det
    that => NP

    I => Pro
    you => Pro
    we => Pro

    chef => N
    cake => N
    children => N
    dough => N

    will => Modal
    should => Modal
    might => Modal
    must => Modal

    and => var\\.,var/.,var

    to => VP[to]/VP

    without => (VP\\VP)/VP[ing]

    be => TV
    cook => TV
    eat => TV

    cooking => VP[ing]/NP

    give => DTV

    is => (S\\NP)/NP
    prefer => (S\\NP)/NP

    which => (N\\N)/(S/NP)

    persuade => (VP/VP[to])/NP
    """


class TestDocumentedLexicons:
    def test_relative_clause_lexicon_parses_as_documented(self):
        lex = fromstring(_RELATIVE_CLAUSES)
        parses, text = _derivation(lex, "you prefer that cake")
        # the doctest prints the first of these derivations and breaks
        assert len(parses) == 7
        assert _rows(text) == [
            "you prefer that cake",
            "NP ((S\\NP)/NP) (NP/N) N",
            (14, ">"),
            "NP",
            (27, ">"),
            "(S\\NP)",
            (32, "<"),
            "S",
        ]
        parses, text = _derivation(lex, "that is the cake which you prefer")
        assert parses and _rows(text)[-1] == "S"

    def test_semantics_lexicons_parse_as_documented(self):
        # nltk/test/ccg_semantics.doctest, "No semantics"
        lex = fromstring(
            ":- S, NP, N\nShe => NP\nhas => (S\\NP)/NP\nbooks => NP\n", False
        )
        parses, text = _derivation(lex, "She has books")
        assert len(parses) == 3
        assert _rows(text) == [
            "She has books",
            "NP ((S\\NP)/NP) NP",
            (20, ">"),
            "(S\\NP)",
            (25, "<"),
            "S",
        ]
        # nltk/test/ccg_semantics.doctest, "Simple semantics"
        lex = fromstring(
            ":- S, NP, N\n"
            "She => NP {she}\n"
            "has => (S\\NP)/NP {\\x y.have(y, x)}\n"
            "a => NP/N {\\P.exists z.P(z)}\n"
            "book => N {book}\n",
            True,
        )
        parses, text = _derivation(lex, "She has a book")
        assert len(parses) == 7
        assert _rows(text)[-1] == "S {have(she,exists x.book(x))}"

    def test_openccg_tinytiny_lexicon_from_the_module(self):
        lex = ccglex.openccg_tinytiny
        assert str(lex.start()) == "S"
        assert str(lex).splitlines()[0] == "I => NP"
        parser = chart.CCGChartParser(lex, chart.DefaultRuleSet)
        assert list(parser.parse("the boys eat the peaches".split()))
        assert list(parser.parse("the boy eats the peach".split()))
        # number agreement through the subscripts: no parse
        assert not list(parser.parse("the boy eat the peach".split()))

    def test_chart_demo_runs_offline(self, capsys):
        chart.demo()
        rows = _rows(capsys.readouterr().out)
        assert rows[0] == "I might cook and eat the bacon"
        assert rows[-1] == "S"


# ==========================================================================
# The pre-fix parser, verbatim, as the reference oracle of the differential audit
# ==========================================================================

# nltk/ccg/lexicon.py as it stood on develop before this change (f4e93738f),
# copied verbatim under private names with its own seven regexes; Token,
# CCGLexicon and the api classes are the unchanged data types both parsers build.
_OLD_PRIM_RE = redos.compile(r"""([A-Za-z]+)(\[[A-Za-z,]+\])?""")
_OLD_NEXTPRIM_RE = redos.compile(r"""([A-Za-z]+(?:\[[A-Za-z,]+\])?)(.*)""")
_OLD_APP_RE = redos.compile(r"""([\\/])([.,_]?)([.,]?)(.*)""")
_OLD_LEX_RE = redos.compile(r"""([\S_]*?[^\s=-])\s*(::|[-=]+>)\s*(.+)""", re.UNICODE)
_OLD_RHS_RE = redos.compile(r"""([^{}]*[^ {}])\s*(\{[^}]+\})?""", re.UNICODE)
_OLD_SEMANTICS_RE = redos.compile(r"""\{([^}]+)\}""", re.UNICODE)
_OLD_COMMENTS_RE = redos.compile("""([^#]*)(?:#.*)?""")


def _old_matchBrackets(string, _depth=0, max_depth=None):
    """Separate the contents matching the first set of brackets from the rest of the input."""
    if max_depth is None:
        max_depth = MAX_PARSE_DEPTH
    if _depth > max_depth:
        raise ValueError(
            f"CCG nesting depth exceeds MAX_PARSE_DEPTH "
            f"({MAX_PARSE_DEPTH}); the input may be "
            "adversarially deep. Raise "
            "nltk.ccg.lexicon.MAX_PARSE_DEPTH to allow it."
        )
    rest = string[1:]
    inside = "("

    while rest != "" and not rest.startswith(")"):
        if rest.startswith("("):
            (part, rest) = _old_matchBrackets(rest, _depth + 1, max_depth)
            inside = inside + part
        else:
            inside = inside + rest[0]
            rest = rest[1:]
    if rest.startswith(")"):
        return (inside + ")", rest[1:])
    raise AssertionError("Unmatched bracket in string '" + string + "'")


def _old_nextCategory(string, _depth=0, max_depth=None):
    """Separate the string for the next portion of the category from the rest of the string"""
    if string.startswith("("):
        return _old_matchBrackets(string, _depth, max_depth)
    return _OLD_NEXTPRIM_RE.match(string).groups()


def _old_parseApplication(app):
    """Parse an application operator"""
    return Direction(app[0], app[1:])


def _old_parseSubscripts(subscr):
    """Parse the subscripts for a primitive category"""
    if subscr:
        return subscr[1:-1].split(",")
    return []


def _old_parsePrimitiveCategory(chunks, primitives, families, var):
    """Parse a primitive category

    If the primitive is the special category 'var', replace it with the
    correct `CCGVar`.
    """
    if chunks[0] == "var":
        if chunks[1] is None:
            if var is None:
                var = CCGVar()
            return (var, var)

    catstr = chunks[0]
    if catstr in families:
        (cat, cvar) = families[catstr]
        if var is None:
            var = cvar
        else:
            cat = cat.substitute([(cvar, var)])
        return (cat, var)

    if catstr in primitives:
        subscrs = _old_parseSubscripts(chunks[1])
        return (PrimitiveCategory(catstr, subscrs), var)
    raise AssertionError(
        "String '" + catstr + "' is neither a family nor primitive category."
    )


def _old_augParseCategory(
    line, primitives, families, var=None, _depth=0, max_depth=None
):
    """Parse a string representing a category, and returns a tuple with
    (possibly) the CCG variable for the category
    """
    if max_depth is None:
        max_depth = MAX_PARSE_DEPTH
    if _depth > max_depth:
        raise ValueError(
            f"CCG nesting depth exceeds MAX_PARSE_DEPTH "
            f"({MAX_PARSE_DEPTH}); the input may be "
            "adversarially deep. Raise "
            "nltk.ccg.lexicon.MAX_PARSE_DEPTH to allow it."
        )
    (cat_string, rest) = _old_nextCategory(line, _depth, max_depth)

    if cat_string.startswith("("):
        (res, var) = _old_augParseCategory(
            cat_string[1:-1], primitives, families, var, _depth + 1, max_depth
        )
    else:
        (res, var) = _old_parsePrimitiveCategory(
            _OLD_PRIM_RE.match(cat_string).groups(), primitives, families, var
        )

    while rest != "":
        app = _OLD_APP_RE.match(rest).groups()
        direction = _old_parseApplication(app[0:3])
        rest = app[3]

        (cat_string, rest) = _old_nextCategory(rest, _depth, max_depth)
        if cat_string.startswith("("):
            (arg, var) = _old_augParseCategory(
                cat_string[1:-1],
                primitives,
                families,
                var,
                _depth + 1,
                max_depth,
            )
        else:
            (arg, var) = _old_parsePrimitiveCategory(
                _OLD_PRIM_RE.match(cat_string).groups(), primitives, families, var
            )
        res = FunctionalCategory(res, arg, direction)

    return (res, var)


def _old_fromstring(lex_str, include_semantics=False, max_depth=None):
    """Convert string representation into a lexicon for CCGs."""
    if max_depth is None:
        max_depth = MAX_PARSE_DEPTH
    CCGVar.reset_id()
    primitives = []
    families = {}
    entries = defaultdict(list)
    for line in lex_str.splitlines():
        # Strip comments and leading/trailing whitespace.
        line = _OLD_COMMENTS_RE.match(line).groups()[0].strip()
        if line == "":
            continue

        if line.startswith(":-"):
            # A line of primitive categories.
            # The first one is the target category
            # ie, :- S, N, NP, VP
            primitives = primitives + [
                prim.strip() for prim in line[2:].strip().split(",")
            ]
        else:
            # Either a family definition, or a word definition
            (ident, sep, rhs) = _OLD_LEX_RE.match(line).groups()
            (catstr, semantics_str) = _OLD_RHS_RE.match(rhs).groups()
            (cat, var) = _old_augParseCategory(
                catstr, primitives, families, max_depth=max_depth
            )

            if sep == "::":
                # Family definition
                # ie, Det :: NP/N
                families[ident] = (cat, var)
            else:
                semantics = None
                if include_semantics is True:
                    if semantics_str is None:
                        raise AssertionError(
                            line
                            + " must contain semantics because include_semantics is set to True"
                        )
                    else:
                        semantics = Expression.fromstring(
                            _OLD_SEMANTICS_RE.match(semantics_str).groups()[0]
                        )
                # Word definition
                # ie, which => (N\N)/(S/NP)
                entries[ident].append(Token(ident, cat, semantics))
    return CCGLexicon(primitives[0], primitives, families, entries)


# ==========================================================================
# Differential machinery: the same input through both parsers, compared whole
# ==========================================================================


def _signature(cat):
    """A category as plain data: every primitive name, subscript, direction,
    modifier and variable id, plus its string form."""
    if isinstance(cat, CCGVar):
        return ("var", cat.id(), str(cat))
    if isinstance(cat, PrimitiveCategory):
        return ("prim", cat.categ(), tuple(cat.restrs()), str(cat))
    if isinstance(cat, FunctionalCategory):
        direction = cat.dir()
        return (
            "fun",
            _signature(cat.res()),
            (direction.dir(), direction.restrs(), direction.is_variable()),
            _signature(cat.arg()),
            str(cat),
        )
    return ("other", repr(cat))


def _var_signature(var):
    return None if var is None else _signature(var)


def _lexicon_signature(lex):
    """A whole lexicon as plain data: start, primitives in order, every family
    with its variable, every entry's categories and semantics, and str()."""
    families = {
        name: (_signature(cat), _var_signature(var))
        for name, (cat, var) in lex._families.items()
    }
    entries = {
        word: [(_signature(tok.categ()), str(tok.semantics())) for tok in toks]
        for word, toks in lex._entries.items()
    }
    return (str(lex.start()), tuple(lex._primitives), families, entries, str(lex))


def _tree_signature(tree):
    """A parse tree as plain data: every token's category and semantics and
    every combinator, down to the words."""
    if not isinstance(tree, Tree):
        return tree
    label = tree.label()
    if isinstance(label, tuple):
        label = (str(label[0]), label[1])
    elif isinstance(label, Token):
        label = str(label)
    return (label, tuple(_tree_signature(child) for child in tree))


def _derivation_text(tree):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        chart.printCCGDerivation(tree)
    return out.getvalue()


def _outcome(fn):
    """``("ok", value)`` or ``("exc", type name, message)``."""
    try:
        return ("ok", fn())
    except Exception as exc:
        return ("exc", type(exc).__name__, str(exc))


def _described(outcome, describe):
    if outcome[0] == "ok":
        return ("ok", describe(outcome[1]))
    return outcome


def _category_outcome(parse, text, primitives, families):
    """One parser's outcome on a category string, as comparable data; the
    variable counter is reset so both sides number their variables alike."""
    CCGVar.reset_id()
    return _described(
        _outcome(lambda: parse(text, primitives, families)),
        lambda pair: (_signature(pair[0]), _var_signature(pair[1])),
    )


def _both_lexicons(text, include_semantics=False):
    """``fromstring`` through the oracle and the fixed parser; the outcomes must
    agree as data. Returns the fixed parser's lexicon carrying the oracle's as
    ``_old_twin``, or raises what both raised."""
    old = _outcome(lambda: _old_fromstring(text, include_semantics))
    new = _outcome(lambda: fromstring(text, include_semantics))
    assert _described(old, _lexicon_signature) == _described(new, _lexicon_signature), (
        text[:200],
        old if old[0] == "exc" else "parsed",
        new if new[0] == "exc" else "parsed",
    )
    if new[0] == "exc":
        return fromstring(text, include_semantics)  # raises the real exception
    new[1]._old_twin = old[1]
    return new[1]


class _DifferentialLexiconModule:
    """Stands in for ``nltk.ccg.lexicon`` in the documented examples."""

    def __init__(self):
        self.calls = 0

    def fromstring(self, lex_str, include_semantics=False, max_depth=None):
        self.calls += 1
        return _both_lexicons(lex_str, include_semantics)

    def __getattr__(self, name):
        return getattr(ccglex, name)


class _DifferentialChartParser(chart.CCGChartParser):
    """The real chart parser over the fixed parser's lexicon, with a twin over
    the oracle's; every parse must give the same trees and derivations."""

    calls = 0

    def __init__(self, lexicon, rules, *args, **kwargs):
        super().__init__(lexicon, rules, *args, **kwargs)
        self._twin = chart.CCGChartParser(lexicon._old_twin, rules, *args, **kwargs)

    def parse(self, tokens):
        type(self).calls += 1
        CCGVar.reset_id()
        new = list(super().parse(tokens))
        CCGVar.reset_id()
        old = list(self._twin.parse(tokens))
        assert [_tree_signature(t) for t in new] == [_tree_signature(t) for t in old]
        assert [_derivation_text(t) for t in new] == [_derivation_text(t) for t in old]
        return iter(new)


class _DifferentialChartModule:
    """Stands in for ``nltk.ccg.chart`` in the documented examples."""

    CCGChartParser = _DifferentialChartParser

    def __getattr__(self, name):
        return getattr(chart, name)


def _run_documented_examples(doctest_name):
    """Execute every example of a CCG doctest file, in order, with both
    modules replaced by their differential stand-ins; an example that raises
    must be one the document expects to raise. Returns the number of lexicons
    parsed and of sentences parsed."""
    text = (pathlib.Path(nltk.test.__file__).parent / doctest_name).read_text(
        encoding="utf-8"
    )
    lexicon_module = _DifferentialLexiconModule()
    _DifferentialChartParser.calls = 0
    namespace = {}

    def rebind():
        namespace["lexicon"] = lexicon_module
        namespace["chart"] = _DifferentialChartModule()
        namespace["CCGChartParser"] = _DifferentialChartParser

    rebind()
    for example in doctest.DocTestParser().get_examples(text):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(example.source, doctest_name, "single"), namespace)
        except Exception as exc:
            assert example.exc_msg, (example.source, repr(exc))
            assert type(exc).__name__ in example.exc_msg, (example.exc_msg, repr(exc))
        rebind()
    return lexicon_module.calls, _DifferentialChartParser.calls


def _source_lexicon_string(relative_path, name):
    """The literal a module-level ``name = fromstring('''...''')`` parses."""
    source = (pathlib.Path(ccglex.__file__).parent / relative_path).read_text(
        encoding="utf-8"
    )
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return node.value.args[0].value
    raise AssertionError(f"{name} not found in {relative_path}")


# ==========================================================================
# Differential audit: the documented grammars
# ==========================================================================


class TestDifferentialDocumentedGrammars:
    def test_ccg_doctest_examples_agree(self):
        # 4 lexicons (relative clauses, test1_lex, test2_lex, Spanish) and the
        # 7 sentences the document parses, trees and derivations compared
        assert _run_documented_examples("ccg.doctest") == (4, 7)

    def test_ccg_semantics_doctest_examples_agree(self):
        # 9 lexicons (six with semantics, the three str() examples, one of
        # them the documented AssertionError) and 6 parsed sentences
        assert _run_documented_examples("ccg_semantics.doctest") == (9, 6)

    def test_module_lexicons_agree_with_their_source_and_the_live_objects(self):
        for relative_path, name, live in (
            ("lexicon.py", "openccg_tinytiny", ccglex.openccg_tinytiny),
            ("chart.py", "lex", chart.lex),
        ):
            text = _source_lexicon_string(relative_path, name)
            lex = _both_lexicons(text)
            assert _lexicon_signature(lex) == _lexicon_signature(live)
        parser = _DifferentialChartParser(
            _both_lexicons(_source_lexicon_string("chart.py", "lex")),
            chart.DefaultRuleSet,
        )
        assert len(list(parser.parse("I might cook and eat the bacon".split()))) == 25


# ==========================================================================
# Differential audit: a generated corpus, fixed seed
# ==========================================================================

_CORPUS_PRIMITIVES = ["S", "NP", "N", "VP", "PP"]
_CORPUS_FAMILIES = ":- S, NP, N, VP, PP\nDet :: NP/N\nTV :: VP/NP\n"
_CORPUS_SEMANTICS = [
    "{\\x.P(x)}",
    "{book}",
    "{\\x y.eat(x,y)}",
    "{sem=\\x.P(x)}",
    "{(((}",
    "{",
    "",
]


class _Corpus:
    """Random lexicon text from the grammar and its neighbourhood: primitives
    with and without subscripts, nests to depth 12, both slashes with every
    modifier combination, variables, families, unknown and lower-case and
    digit-bearing and accented names, empty and malformed subscripts, doubled
    and spaced and foreign operators, embedded line breaks and tabs, trailing
    garbage, semantics blocks, comments and odd separators."""

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def subscript(self):
        return self.rng.choice(
            ["", "", "[sg]", "[pl]", "[sg,pl]", "[]", "[1]", "[a,]", "[ing", "[x y]"]
        )

    def atom(self, depth):
        roll = self.rng.random()
        if roll < 0.08 and depth < 12:
            return "(" + self.category(depth + 1) + ")"
        if roll < 0.12:
            return self.rng.choice(
                [
                    "var",
                    "var[sg]",
                    "Det",
                    "TV",
                    "X",
                    "s",
                    "np",
                    "N1",
                    "é",
                    "ñp",
                    "",
                    " ",
                    "S N",
                    "(",
                    ")",
                    "S)",
                ]
            )
        return self.rng.choice(_CORPUS_PRIMITIVES) + self.subscript()

    def operator(self):
        return self.rng.choice(
            [
                "/",
                "\\",
                "/.",
                "\\.",
                "/,",
                "\\,",
                "/_",
                "\\_",
                "/.,",
                "\\,.",
                "/_,",
                "//",
                "/ ",
                "",
                "|",
                "\n/",
                "/\n",
            ]
        )

    def category(self, depth=0):
        text = self.atom(depth)
        for _ in range(self.rng.randint(0, 4)):
            text += self.operator() + self.atom(depth)
        if self.rng.random() < 0.05:
            text += self.rng.choice(
                [")", "(", "\n", "\nN", "\t", " ", "{x}", "#c", "1", "_", "S"]
            )
        return text

    def lexicon(self):
        lines = [
            self.rng.choice(
                [
                    ":- S, NP, N, VP, PP",
                    ":- S,NP,N,VP,PP",
                    ":-S, NP",
                    ":- S",
                    "",
                    "# only comment",
                ]
            )
        ]
        for _ in range(self.rng.randint(0, 6)):
            ident = self.rng.choice(
                [
                    "the",
                    "Det",
                    "TV",
                    "eat",
                    "a-b",
                    "x/y",
                    "é",
                    "w" + str(self.rng.randint(0, 9)),
                    "and",
                    "",
                ]
            )
            separator = self.rng.choice(
                [" => ", "=>", " :: ", "::", " ==> ", " -> ", " ", " = "]
            )
            semantics = (
                self.rng.choice(_CORPUS_SEMANTICS) if self.rng.random() < 0.3 else ""
            )
            line = (
                ident
                + separator
                + self.category()
                + (" " + semantics if semantics else "")
            )
            if self.rng.random() < 0.2:
                line += "  # " + self.rng.choice(["c", "#", "{", "=>"])
            if self.rng.random() < 0.1:
                line = "   " + line + "\t"
            lines.append(line)
        return self.rng.choice(["\n", "\r\n", "\r"]).join(lines) + self.rng.choice(
            ["", "\n"]
        )


def _category_divergences(count, seed):
    """Every generated category whose outcome differs between the oracle and
    the fixed parser, as ``(index, text, old, new)``."""
    corpus = _Corpus(seed)
    old_families = _old_fromstring(_CORPUS_FAMILIES)._families
    new_families = fromstring(_CORPUS_FAMILIES)._families
    divergences = []
    for index in range(count):
        text = corpus.category()
        old = _category_outcome(
            _old_augParseCategory, text, _CORPUS_PRIMITIVES, old_families
        )
        new = _category_outcome(
            augParseCategory, text, _CORPUS_PRIMITIVES, new_families
        )
        if old != new:
            divergences.append((index, text, old, new))
    return divergences


class TestDifferentialGeneratedCorpus:
    def test_categories_differ_only_on_an_embedded_line_break(self):
        divergences = _category_divergences(6_000, 20261001)
        # The one divergence class: the oracle's trailing (.*) stopped at a
        # line break and silently dropped the rest; the fixed parser sees it
        assert all("\n" in text for _, text, _, _ in divergences), divergences[:3]
        assert all(new[0] == "exc" for _, _, _, new in divergences)
        index, text, old, new = divergences[0]
        assert (index, text) == (11, "VP\n/PP[]//NP[]/.,S[1]")
        assert old[0] == "ok" and old[1][0][3] == "VP"
        assert new[:2] == ("exc", "AttributeError")
        assert len(divergences) == 273

    def test_categories_without_a_line_break_never_differ(self):
        corpus = _Corpus(20261001)
        old_families = _old_fromstring(_CORPUS_FAMILIES)._families
        new_families = fromstring(_CORPUS_FAMILIES)._families
        checked = 0
        for _ in range(6_000):
            text = corpus.category().replace("\n", "")
            old = _category_outcome(
                _old_augParseCategory, text, _CORPUS_PRIMITIVES, old_families
            )
            new = _category_outcome(
                augParseCategory, text, _CORPUS_PRIMITIVES, new_families
            )
            assert old == new, (text, old, new)
            checked += 1
        assert checked == 6_000

    def test_lexicons_never_differ(self):
        # fromstring splits lines before any category is parsed, so the one
        # category-level divergence cannot be reached through it
        corpus = _Corpus(20261002)
        parsed = refused = 0
        for _ in range(3_000):
            text = corpus.lexicon()
            include_semantics = corpus.rng.random() < 0.3
            old = _outcome(lambda: _old_fromstring(text, include_semantics))
            new = _outcome(lambda: fromstring(text, include_semantics))
            assert _described(old, _lexicon_signature) == _described(
                new, _lexicon_signature
            ), (text, old, new)
            if new[0] == "ok":
                parsed += 1
            else:
                refused += 1
        assert parsed >= 300 and refused >= 300, (parsed, refused)


# ==========================================================================
# Differential audit: complete, valid CCG inputs, short and long, with repeats
# ==========================================================================

# An English fragment using every construct of the lexicon syntax at once:
# features, families built on families, several categories per word, modality
# and variable-direction slashes, conjunction over var, a relativiser, comments.
_COMPLETE_FRAGMENT = r"""
    # primitives; S is the start
    :- S, NP, N, PP, VP

    Det :: NP[sg]/N[sg]
    DetPl :: NP[pl]/N[pl]
    Pro :: NP
    IV :: S\NP
    TV :: (S\NP)/NP
    DTV :: TV/NP
    Modal :: (S\NP)/VP
    Adv :: (S\NP)\(S\NP)
    Prep :: (NP\NP)/NP
    Conj :: var\.,var/.,var
    Rel :: (N[sg]\N[sg])/(S/NP)

    the => Det
    the => DetPl
    a => Det
    every => Det
    I => Pro
    you => Pro
    we => Pro

    chef => N[sg]
    chefs => N[pl]
    cake => N[sg]
    cakes => N[pl]
    dough => N[sg]
    knife => N[sg]

    bake => TV
    bakes => TV
    eat => TV
    eats => TV
    sleep => IV
    sleeps => IV
    give => DTV
    gives => DTV
    will => Modal
    might => Modal
    cook => VP/NP
    eat => VP/NP

    quickly => Adv
    with => Prep
    and => Conj
    which => Rel
    that => Rel
    that => Det
    well => (S\_NP)/(S\_NP)
"""

# The same constructs with a lambda term on every word
_COMPLETE_SEMANTIC_FRAGMENT = r"""
    :- S, NP, N
    Det :: NP[sg]/N[sg]
    Pro :: NP
    IV :: S\NP
    TV :: (S\NP)/NP
    the => Det {\P Q.exists x.(P(x) & Q(x))}
    a => Det {\P Q.exists x.(P(x) & Q(x))}
    I => Pro {me}
    chef => N[sg] {\x.chef(x)}
    cake => N[sg] {\x.cake(x)}
    sleeps => IV {\x.sleep(x)}
    bakes => TV {\x y.bake(y,x)}
    eat => TV {\x y.eat(y,x)}
    and => var\.,var/.,var {\x y.(x & y)}
"""

# Sentences over the fragment and the derivations the real chart finds under
# each rule set (measured, both parsers agreeing); 0 where nothing closes
_COMPLETE_SENTENCES = [
    "the chef bakes the cake",
    "I eat the cake",
    "the chefs eat the cakes",
    "we will cook the dough",
    "the chef gives the chef the cake",
    "the chef eats the cake which I bake",
    "I bake and eat the cake",
    "the chef sleeps quickly",
    "the chef eats the cake with the knife",
    "every chef might eat a cake",
    "the chef and the chef sleep",
    "you sleep well",
    "chef the bakes",
    "the chefs sleeps",
    "the cake",
    "eats",
]
_RULE_SETS = {
    "default": chart.DefaultRuleSet,
    "application": chart.ApplicationRuleSet,
    "application+composition": chart.ApplicationRuleSet + chart.CompositionRuleSet,
    "application+composition+substitution": chart.ApplicationRuleSet
    + chart.CompositionRuleSet
    + chart.SubstitutionRuleSet,
    "application+composition+substitution+type-raising": chart.ApplicationRuleSet
    + chart.CompositionRuleSet
    + chart.SubstitutionRuleSet
    + chart.TypeRaiseRuleSet,
}
_COMPLETE_COUNTS = {
    "default": [2, 7, 2, 19, 4, 11, 7, 1, 2, 5, 1, 0, 0, 1, 0, 0],
    "application": [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0],
    "application+composition": [2, 2, 2, 5, 4, 0, 2, 1, 2, 5, 1, 0, 0, 1, 0, 0],
    "application+composition+substitution": [
        2,
        2,
        2,
        5,
        4,
        0,
        2,
        1,
        2,
        5,
        1,
        0,
        0,
        1,
        0,
        0,
    ],
    "application+composition+substitution+type-raising": [
        2,
        7,
        2,
        19,
        4,
        11,
        7,
        1,
        2,
        5,
        1,
        0,
        0,
        1,
        0,
        0,
    ],
}


# A CCGbank-style fragment: verb-form features on embedded clauses (S[b],
# S[to], S[pss], S[em]), control, passive, questions, relatives, adjuncts
_CCGBANK_STYLE_FRAGMENT = r"""
    :- S, NP, N, PP
    the => NP/N
    a => NP/N
    company => N
    shares => N
    shares => NP
    investors => NP
    Smith => NP
    bought => (S\NP)/NP
    rose => S\NP
    fell => S\NP
    said => (S\NP)/S[em]
    plans => (S\NP)/(S[to]\NP)
    plan => (S\NP)/(S[to]\NP)
    were => (S\NP)/(S[pss]\NP)
    buy => (S[b]\NP)/NP
    bought => S[pss]\NP
    to => (S[to]\NP)/(S[b]\NP)
    that => S[em]/S
    that => (NP\NP)/(S\NP)
    that => (NP\NP)/(S/NP)
    by => ((S[pss]\NP)\(S[pss]\NP))/NP
    did => (S/(S[b]\NP))/NP
    sharply => (S\NP)\(S\NP)
    yesterday => (S\NP)\(S\NP)
    in => ((S\NP)\(S\NP))/NP
    in => (NP\NP)/NP
    and => var\.,var/.,var
"""
_CCGBANK_SENTENCES = [
    "the company bought the shares",
    "shares rose sharply",
    "Smith said that the shares rose",
    "the company plans to buy shares",
    "shares were bought by the company",
    "did the company buy shares",
    "the shares that the company bought rose",
    "the company that bought shares rose",
    "investors and the company bought shares",
    "the company bought shares in the company yesterday",
    "Smith said that investors plan to buy shares",
    "the company bought and investors bought shares",
    "company the bought",
    "shares were buy",
    "the company plans buy shares",
    "rose",
]
_CCGBANK_COUNTS = {
    "default": [7, 1, 12, 19, 6, 4, 8, 20, 4, 110, 635, 8, 0, 0, 0, 0],
    "application": [1, 1, 1, 1, 1, 1, 0, 2, 1, 2, 1, 1, 0, 0, 0, 0],
    "application+composition": [2, 1, 2, 5, 2, 4, 0, 8, 1, 6, 10, 1, 0, 0, 0, 0],
}


def _long_lexicon(copies, extra_words):
    """The complete fragment declared ``copies`` times over, then ``extra_words``
    nouns and verbs on its families: a long, valid lexicon with repeats."""
    kinds = ("N[sg]", "N[pl]", "TV", "IV")
    extra = "".join(
        _name(i).lower() + " => " + kinds[i % 4] + "\n" for i in range(extra_words)
    )
    return _COMPLETE_FRAGMENT * copies + extra


class TestDifferentialCompleteGrammars:
    def test_complete_fragment_parses_identically(self):
        lex = _both_lexicons(_COMPLETE_FRAGMENT)
        assert lex._primitives == ["S", "NP", "N", "PP", "VP"]
        assert sorted(lex._families) == sorted(
            "Det DetPl Pro IV TV DTV Modal Adv Prep Conj Rel".split()
        )
        assert len(lex._entries) == 29
        assert [str(c) for c in lex.categories("the")] == [
            "(NP['sg']/N['sg'])",
            "(NP['pl']/N['pl'])",
        ]
        assert [str(c) for c in lex.categories("that")] == [
            "((N['sg']\\N['sg'])/(S/NP))",
            "(NP['sg']/N['sg'])",
        ]
        assert str(lex.categories("gives")[0]) == "(((S\\NP)/NP)/NP)"
        assert str(lex.categories("and")[0]) == "((_var0\\.,_var0)/.,_var0)"
        assert lex.categories("well")[0].categ().dir().is_forward()

    @pytest.mark.parametrize("rules", list(_RULE_SETS), ids=list(_RULE_SETS))
    def test_complete_fragment_sentences_parse_alike_under_every_rule_set(self, rules):
        lex = _both_lexicons(_COMPLETE_FRAGMENT)
        parser = _DifferentialChartParser(lex, _RULE_SETS[rules])
        counts = [len(list(parser.parse(s.split()))) for s in _COMPLETE_SENTENCES]
        assert counts == _COMPLETE_COUNTS[rules]

    def test_complete_fragment_derivation_as_the_chart_prints_it(self):
        lex = _both_lexicons(_COMPLETE_FRAGMENT)
        parser = _DifferentialChartParser(lex, chart.DefaultRuleSet)
        parses = list(parser.parse("I bake and eat the cake".split()))
        rows = _rows(_derivation_text(parses[0]))
        assert rows[0] == "I bake and eat the cake"
        assert rows[1] == (
            "NP ((S\\NP)/NP) ((_var0\\.,_var0)/.,_var0) ((S\\NP)/NP) "
            "(NP['sg']/N['sg']) N['sg']"
        )
        assert rows[-1] == "S"

    def test_complete_semantic_fragment_parses_alike_with_its_lambda_terms(self):
        lex = _both_lexicons(_COMPLETE_SEMANTIC_FRAGMENT, include_semantics=True)
        parser = _DifferentialChartParser(lex, chart.DefaultRuleSet)
        expected = {
            "the chef sleeps": (1, "sleep(\\P.exists x.(chef(x) & P(x)))"),
            "I eat the cake": (7, "eat(me,\\P.exists x.(cake(x) & P(x)))"),
            "the chef bakes a cake": (
                2,
                "bake(\\P.exists x.(chef(x) & P(x)),\\Q.exists y.(cake(y) & Q(y)))",
            ),
        }
        for sentence, (count, semantics) in expected.items():
            parses = list(parser.parse(sentence.split()))
            assert len(parses) == count, sentence
            assert {str(p.label()[0].semantics()) for p in parses} == {semantics}

    def test_ccgbank_style_fragment_parses_identically(self):
        lex = _both_lexicons(_CCGBANK_STYLE_FRAGMENT)
        assert lex._primitives == ["S", "NP", "N", "PP"]
        assert len(lex._entries) == 22
        assert [str(c) for c in lex.categories("that")] == [
            "(S['em']/S)",
            "((NP\\NP)/(S\\NP))",
            "((NP\\NP)/(S/NP))",
        ]
        assert str(lex.categories("by")[0]) == "(((S['pss']\\NP)\\(S['pss']\\NP))/NP)"
        assert str(lex.categories("did")[0]) == "((S/(S['b']\\NP))/NP)"

    @pytest.mark.parametrize("rules", list(_CCGBANK_COUNTS), ids=list(_CCGBANK_COUNTS))
    def test_ccgbank_style_sentences_parse_alike(self, rules):
        lex = _both_lexicons(_CCGBANK_STYLE_FRAGMENT)
        parser = _DifferentialChartParser(lex, _RULE_SETS[rules])
        counts = [len(list(parser.parse(s.split()))) for s in _CCGBANK_SENTENCES]
        assert counts == _CCGBANK_COUNTS[rules]

    def test_ccgbank_style_derivations_as_the_chart_prints_them(self):
        lex = _both_lexicons(_CCGBANK_STYLE_FRAGMENT)
        parser = _DifferentialChartParser(lex, chart.DefaultRuleSet)
        passive = _rows(
            _derivation_text(
                list(parser.parse("shares were bought by the company".split()))[0]
            )
        )
        assert passive[0] == "shares were bought by the company"
        assert passive[1] == (
            "NP ((S\\NP)/(S['pss']\\NP)) (S['pss']\\NP) "
            "(((S['pss']\\NP)\\(S['pss']\\NP))/NP) (NP/N) N"
        )
        assert [row for row in passive if isinstance(row, str)][2:] == [
            "NP",
            "((S['pss']\\NP)\\(S['pss']\\NP))",
            "(S['pss']\\NP)",
            "(S\\NP)",
            "S",
        ]
        question = _rows(
            _derivation_text(
                list(parser.parse("did the company buy shares".split()))[0]
            )
        )
        assert question[1] == "((S/(S['b']\\NP))/NP) (NP/N) N ((S['b']\\NP)/NP) NP"
        assert [row for row in question if isinstance(row, str)][2:] == [
            "NP",
            "(S/(S['b']\\NP))",
            "(S['b']\\NP)",
            "S",
        ]

    @pytest.mark.parametrize("copies, extra_words", [(3, 300), (5, 1000)])
    def test_long_lexicon_with_repeats_parses_identically(self, copies, extra_words):
        lex = _both_lexicons(_long_lexicon(copies, extra_words))
        # every repeated declaration is kept, in order, on both parsers
        assert lex._primitives == ["S", "NP", "N", "PP", "VP"] * copies
        assert lex._old_twin._primitives == lex._primitives
        assert str(lex.start()) == "S"
        assert len(lex._entries) == 29 + extra_words
        assert len(lex.categories("the")) == 2 * copies
        assert [str(c) for c in lex.categories("sleeps")] == ["(S\\NP)"] * copies
        assert [str(c) for c in lex.categories("pa")] == ["N['sg']"]
        # repeated identical entries leave the chart's derivations as they were
        for rules, counts in (("default", [1, 2, 1]), ("application", [1, 1, 1])):
            parser = _DifferentialChartParser(lex, _RULE_SETS[rules])
            found = [
                len(list(parser.parse(s.split())))
                for s in ("the chef sleeps", "the chef bakes the cake", "the pa sleeps")
            ]
            assert found == counts, (rules, found)


# ==========================================================================
# The two points where the fixed parser departs from the oracle, pinned
# ==========================================================================


class TestDeparturesFromThePreFixParser:
    def test_line_break_inside_a_category_is_refused_not_truncated(self):
        # Directly: the oracle returned VP and dropped "/PP"; the fixed parser
        # refuses, as it does every malformed category
        CCGVar.reset_id()
        old, _ = _old_augParseCategory("VP\n/PP", _CORPUS_PRIMITIVES, {})
        assert str(old) == "VP"
        with pytest.raises(AttributeError):
            augParseCategory("VP\n/PP", _CORPUS_PRIMITIVES, {})
        # Through fromstring the break is a line boundary for both parsers
        lex = _both_lexicons(":- S, VP, PP\nw => VP\nv => PP\n")
        assert sorted(lex._entries) == ["v", "w"]
        with pytest.raises(AttributeError):
            _old_fromstring(":- S, VP, PP\nw => VP\n/PP\n")
        with pytest.raises(AttributeError):
            fromstring(":- S, VP, PP\nw => VP\n/PP\n")

    def test_repeated_primitive_declarations_keep_the_list_and_parse_alike(self):
        # The set is an index for the membership test only: the lexicon's list
        # keeps every declaration, repeats and order included, as on develop
        text = (
            ":- S, NP, S, N\n:- NP\nDet :: NP/N\nthe => Det\ncake => N\n"
            "sleeps => S\\NP\n"
        )
        lex = _both_lexicons(text)  # compares _primitives as data too
        assert lex._primitives == ["S", "NP", "S", "N", "NP"]
        assert lex._old_twin._primitives == ["S", "NP", "S", "N", "NP"]
        assert str(lex.start()) == "S"
        assert [str(c) for c in lex.categories("the")] == ["(NP/N)"]
        parser = _DifferentialChartParser(lex, chart.DefaultRuleSet)
        parses = list(parser.parse("the cake sleeps".split()))
        assert len(parses) == 1 and _rows(_derivation_text(parses[0]))[-1] == "S"

    def test_the_cap_is_the_only_size_departure(self):
        # Exactly MAX_PARSE_LEN: both parse, identically
        exact = "S[" + "a," * ((MAX_PARSE_LEN - 4) // 2) + "a]"
        assert len(exact) == MAX_PARSE_LEN
        assert _category_outcome(
            _old_augParseCategory, exact, ["S"], {}
        ) == _category_outcome(augParseCategory, exact, ["S"], {})
        # One more: the oracle accepts it (in milliseconds, the sink is not the
        # subscript scan), the fixed parser refuses it by the cap
        over = exact[:-1] + "a]"
        assert len(over) == MAX_PARSE_LEN + 1
        with timing.budget(
            2.0, "the oracle on a 100001-char primitive", cpu_bound=True
        ):
            old, _ = _old_augParseCategory(over, ["S"], {})
        assert len(old.restrs()) == (MAX_PARSE_LEN - 4) // 2 + 1
        with pytest.raises(ValueError, match="MAX_PARSE_LEN"):
            augParseCategory(over, ["S"], {})
