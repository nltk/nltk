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

import contextlib
import io
import string

import pytest

from nltk.ccg import chart
from nltk.ccg import lexicon as ccglex
from nltk.ccg.api import FunctionalCategory
from nltk.ccg.lexicon import (
    MAX_PARSE_DEPTH,
    MAX_PARSE_LEN,
    augParseCategory,
    fromstring,
    matchBrackets,
    nextCategory,
)
from nltk.sem.logic import LogicalExpressionException
from nltk.termsec import sanitize_terminal
from nltk.test.unit import timing

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
        # The input and sizes the probe measures, through the same helper:
        # the cursor parser reads ~4x, the tail re-slicer it replaced ~13x
        ratio = timing.scaling_ratio(
            lambda n: fromstring(_chain(n)), 10_000, 40_000, cpu_bound=True
        )
        assert ratio < timing.QUADRATIC_RATIO, ratio

    def test_probe_shape_is_a_real_parse(self):
        cat = fromstring(_chain(40_000)).categories("w")[0].categ()
        assert _applications(cat) == 40_000

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
