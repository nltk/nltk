# Natural Language Toolkit: expanded ReDoS candidate sweep
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""Broadened adversarial sweep for the ``nltk.redos`` ReDoS / algorithmic-DoS
chokepoint (GHSA-8mgp umbrella, CWE-1333 / CWE-400).

Every regular expression in NLTK routes through :mod:`nltk.redos`, so a
catastrophically backtracking pattern, a hostile *input* against an otherwise
innocent pattern, or an oversized / deeply nested / counted-repetition source
must never hang a CPU core. This module widens the proven-candidate battery
beyond ``test_redos.py`` and ``test_attack_dos_expanded.py``:

* **Match-time backtracking** -- identical / overlapping alternation branches
  (``(a|a)*$`` and relatives) and ``.*``-driven counted groups (``(.*a){25}z``)
  that neither ``re`` nor the ``regex`` optimiser linearises: only the
  wall-clock timeout stops them, and it MUST fire.
* **Malicious input, innocent pattern** -- the same fixed pattern returns fast
  on a benign input but must be *bounded* (timeout fires) on a crafted long
  input; ``re`` alone would hang.
* **Compile-time refusal** -- a source past ``MAX_PATTERN_LENGTH``, nested past
  ``MAX_NESTING_DEPTH``, or with a counted repetition past ``MAX_REPEAT_PRODUCT``
  (plus huge alternations and giant ``{...}`` counts) is refused before any
  engine sees it.
* **Caller sinks** -- ``RegexpStemmer`` / ``RegexpTokenizer`` / ``RegexpTagger``
  / ``featstruct`` rename / ``Valuation`` parse / chunk rules / ``tgrep`` are fed
  a hostile pattern or input and asserted bounded (refused or fast), never hung.
* **Benign controls** -- ordinary regexes still compile and match correctly and
  quickly, and legitimately large-but-safe inputs still process.

The batteries that could genuinely *hang* if a guard were removed run in a fresh
child interpreter under a hard :mod:`subprocess` wall-clock budget (the same
plumbing style as ``test_attack_dos_expanded.py``): a removed guard shows up as
``subprocess.TimeoutExpired`` and *fails* the test rather than wedging the suite.
The compile-refusal and benign batteries cannot hang (refusal is instant, benign
input is linear), so they run in-process for speed and exactness.
"""

import os
import subprocess
import sys
import time
from collections import namedtuple

import pytest

from nltk import redos
from nltk.redos import MAX_NESTING_DEPTH, MAX_PATTERN_LENGTH, MAX_REPEAT_PRODUCT

# ==========================================================================
# Subprocess plumbing (a genuine hang -> TimeoutExpired -> test failure)
# ==========================================================================

# Head-room over the child's short redos timeout plus a cold ``import nltk`` on a
# loaded machine. A guarded child that does not finish inside this really hung.
GUARDED_BUDGET = 40.0
# A stock (unguarded) control is expected to spin forever; this is only how long
# we wait before concluding "yes, it hangs". Short: the stdlib sink imports only
# ``re`` / ``regex``.
STOCK_TEETH_TIMEOUT = 8.0

_ChildResult = namedtuple("_ChildResult", "timed_out returncode cases stdout stderr")


def _parse_cases(stdout):
    cases = {}
    for line in (stdout or "").splitlines():
        if line.startswith("CASE|"):
            parts = line.split("|", 3)
            if len(parts) >= 3:
                cases[parts[1]] = parts[2]
    return cases


def _run_child(code, budget):
    """Run ``code`` in a fresh interpreter under a hard wall-clock ``budget``.

    The child inherits the parent's ``sys.path`` so it imports the very NLTK
    under test, and a cold import cannot be mistaken for a hang.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=budget,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        out, err = exc.stdout or "", exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return _ChildResult(True, None, _parse_cases(out), out, err)
    return _ChildResult(
        False, proc.returncode, _parse_cases(proc.stdout), proc.stdout, proc.stderr
    )


def _assert_no_hang(res, family):
    assert not res.timed_out, (
        f"{family}: a guarded sink did NOT return inside {GUARDED_BUDGET}s "
        f"(possible hang / removed guard). stdout so far:\n{res.stdout}\n"
        f"stderr:\n{res.stderr}"
    )


def _assert_cases(res, expected):
    for name, allowed in expected.items():
        assert name in res.cases, (
            f"case {name!r} never reported (child crashed before it?).\n"
            f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )
        assert res.cases[name] in allowed, (
            f"case {name!r} reported {res.cases[name]!r}, expected one of "
            f"{sorted(allowed)}.\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )


# A short redos timeout keeps the timeout-family cases fast; ``report`` /
# ``guarded`` mirror the reporting protocol used across the DoS suites.
_CHILD_PREAMBLE = r"""
import sys, re, time
import nltk.redos as _R
_R.DEFAULT_TIMEOUT = 0.5
from nltk import redos

def report(name, verdict, detail=""):
    print("CASE|%s|%s|%s" % (name, verdict, detail))
    sys.stdout.flush()

def guarded(name, fn, refusing=(ValueError, TimeoutError, re.error)):
    start = time.perf_counter()
    try:
        fn()
        report(name, "BOUNDED", "%.3f" % (time.perf_counter() - start))
    except refusing as e:
        report(name, "REFUSED", type(e).__name__)
    except Exception as e:  # noqa
        report(name, "ERROR", "%s:%s" % (type(e).__name__, str(e)[:60]))
"""


# ==========================================================================
# Confirmed pattern families (empirically triaged against the real guard)
# ==========================================================================

#: Alternation of identical / overlapping branches: neither ``re`` nor the
#: ``regex`` optimiser linearises these, so ONLY the wall-clock timeout stops the
#: exponential backtracking -> the timeout MUST fire (REFUSED with TimeoutError).
#: Each pattern is paired with the specific bait that drives its backtracking
#: (a generic all-``a`` bait would leave a ``\d`` / ``ab`` pattern with nothing
#: to backtrack over, so it would finish fast and mask a removed guard).
TIMEOUT_FAMILY = [
    (r"(a|a)*$", "a" * 96 + "!"),  # two identical single-char branches
    (r"(a|a|a|a)*$", "a" * 96 + "!"),  # four identical branches
    (r"(aa|aa)*$", "a" * 96 + "!"),  # identical two-char branches
    (r"(ab|ab)*$", "ab" * 48 + "!"),  # identical multi-char branches
    (r"([ab]|[ab])*$", "a" * 96 + "!"),  # identical character-class branches
    (r"(a|a)+b", "a" * 96),  # ``+`` instead of ``*``
    (r"(a|a){10,}$", "a" * 96 + "!"),  # counted-open alternation loop
    (r"(\d|\d)*$", "1" * 96 + "!"),  # identical metacharacter branches
]

#: Nested quantifiers / backreference / lookahead shapes the ``regex`` optimiser
#: DOES linearise: these must finish fast and must NOT raise (kept so a future
#: engine regression that reverts them to hangs -- which the timeout would then
#: have to catch -- is visible).
DEFUSED_FAMILY = [
    r"(a+)+$",
    r"(a*)*$",
    r"((a*)*)*$",
    r"([a-z]+)*$",
    r"(a?){30}a{30}",
    r"^(([a-z])+.)+[A-Z]([a-z])+$",
    r"(\w+\s?)*$",
    r"(a+)+\1$",  # backreference blow-up, linearised
    r"(?=(a+))\1a",  # unbounded lookahead + backref, linearised
    r"(\d+)*$",
    r"(a|a|b)*$",  # a single distinct branch lets the engine defuse it
]


# ==========================================================================
# Family 1: match-time backtracking -- the timeout MUST fire (subprocess)
# ==========================================================================


def _redos_match_child():
    body = _CHILD_PREAMBLE + "\n"
    for i, (pat, bait) in enumerate(TIMEOUT_FAMILY):
        body += f"guarded('to_{i}', lambda: redos.compile({pat!r}).search({bait!r}))\n"
    # ``(.*a){25}z`` catastrophically backtracks in BOTH engines on a long,
    # z-less input: the timeout is the only thing that stops it.
    body += "guarded('nested_dotstar', lambda: redos.compile(r'(.*a){25}z').search('a'*400))\n"
    for i, pat in enumerate(DEFUSED_FAMILY):
        body += (
            f"guarded('def_{i}', lambda: redos.compile({pat!r}).search('a'*96+'!'))\n"
        )
    return body


def test_match_time_backtracking_families_bounded():
    res = _run_child(_redos_match_child(), GUARDED_BUDGET)
    _assert_no_hang(res, "match-time backtracking")
    expected = {}
    # Every timeout-family pattern MUST hit the wall-clock cap (REFUSED).
    for i in range(len(TIMEOUT_FAMILY)):
        expected[f"to_{i}"] = {"REFUSED"}
    expected["nested_dotstar"] = {"REFUSED"}
    # Every defused-family pattern MUST finish fast (BOUNDED), never raise.
    for i in range(len(DEFUSED_FAMILY)):
        expected[f"def_{i}"] = {"BOUNDED"}
    _assert_cases(res, expected)


# ==========================================================================
# Family 2: malicious input against an otherwise innocent pattern
# ==========================================================================


def _malicious_input_child():
    return (
        _CHILD_PREAMBLE
        + r"""
# The SAME fixed pattern: benign short input returns instantly; a crafted long
# input drives catastrophic backtracking that the timeout must cut off. This is
# the classic "innocent validator, hostile payload" ReDoS.
P1 = r"(.*a){25}z"
guarded("innocent_short_input", lambda: redos.compile(P1).search("aaz"))
guarded("innocent_long_input",  lambda: redos.compile(P1).search("a" * 500))

# An anchored identical-branch alternation: a valid all-``a`` string matches to
# the ``$`` on the first try (fast), but appending a single trailing byte makes
# the ``$`` fail and forces catastrophic backtracking over the ``a``-run -- a
# hang under stock ``re``, bounded here by the timeout. Same pattern, the input
# is the whole difference.
P2 = r"(a|a)*$"
guarded("overlap_benign_input", lambda: redos.compile(P2).search("a" * 90))
guarded("overlap_hostile_input", lambda: redos.compile(P2).search("a" * 90 + "!"))

# findall / finditer / split / sub over the hostile input are each bounded too
# (the timeout wraps every match method, not just search).
guarded("hostile_findall",  lambda: redos.compile(r"(a|a)*$").findall("a" * 90 + "!"))
guarded("hostile_finditer", lambda: list(redos.compile(r"(a|a)*$").finditer("a" * 90 + "!")))
guarded("hostile_split",    lambda: redos.compile(r"(a|a)*$").split("a" * 90 + "!"))
guarded("hostile_sub",      lambda: redos.compile(r"(a|a)*$").sub("x", "a" * 90 + "!"))
"""
    )


def test_malicious_input_innocent_pattern_bounded():
    res = _run_child(_malicious_input_child(), GUARDED_BUDGET)
    _assert_no_hang(res, "malicious input / innocent pattern")
    _assert_cases(
        res,
        {
            "innocent_short_input": {"BOUNDED"},
            "innocent_long_input": {"REFUSED"},
            "overlap_benign_input": {"BOUNDED"},
            "overlap_hostile_input": {"REFUSED"},
            "hostile_findall": {"REFUSED"},
            "hostile_finditer": {"REFUSED"},
            "hostile_split": {"REFUSED"},
            "hostile_sub": {"REFUSED"},
        },
    )


# ==========================================================================
# Family 3: caller sinks fed a hostile pattern / input (subprocess)
# ==========================================================================


def _caller_sinks_child():
    return (
        _CHILD_PREAMBLE
        + r"""
BAIT = "a" * 96 + "!"

from nltk.stem.regexp import RegexpStemmer
guarded("stemmer_overlap", lambda: RegexpStemmer(r"(a|a)*$").stem(BAIT))
guarded("stemmer_nested",  lambda: RegexpStemmer(r"(.*a){25}z").stem("a" * 300))

from nltk.tokenize import RegexpTokenizer
guarded("tokenizer_overlap", lambda: RegexpTokenizer(r"(a|a)*$").tokenize(BAIT))
guarded("tokenizer_gaps",    lambda: list(RegexpTokenizer(r"(a|a)*$", gaps=True).span_tokenize(BAIT)))

from nltk.tag import RegexpTagger
guarded("tagger_nested", lambda: RegexpTagger([(r"(.*a){25}z", "X"), (r".*", "NN")]).tag([BAIT]))

# featstruct: a caller variable name whose long digit run drives the (now
# linear) trailing-digit strip; both trailing and interior runs must stay fast.
from nltk.featstruct import FeatStruct
guarded("featstruct_trailing_digits", lambda: FeatStruct("[a=?x" + "0" * 100000 + "]").rename_variables())
guarded("featstruct_interior_digits", lambda: FeatStruct("[a=?x" + "0" * 100000 + "z]").rename_variables())

# valuation: a long run of the separator's leading char must split in linear
# time. The hostile line has no valid separator, so parsing may raise its own
# (fast) error -- the security property is that it returns quickly, not hangs.
from nltk.sem.evaluate import read_valuation
def _val():
    try:
        read_valuation("sym " + "=" * 300000)
    except Exception:  # noqa -- a fast parse error is fine; a hang is not
        pass
guarded("valuation_long_run", _val)

# chunk rule whose tag pattern derives an identical-branch backtracking regex.
from nltk.chunk.regexp import ChunkRule, RegexpChunkParser
def _chunk():
    RegexpChunkParser([ChunkRule("<a|a>*<b>", "x")], chunk_label="NP").parse([("a", "a")] * 96)
guarded("chunk_overlap_tag", _chunk)

# tgrep /regex/ node literal over a hostile node label.
try:
    from nltk.tgrep import tgrep_compile, tgrep_nodes
    from nltk.tree import ParentedTree
    _tree = ParentedTree("a" * 96, ["x"])
    guarded("tgrep_overlap", lambda: list(tgrep_nodes(tgrep_compile("/(a|a)*$/"), [_tree])))
except ImportError:
    report("tgrep_overlap", "BOUNDED", "pyparsing-absent")
"""
    )


def test_caller_sinks_hostile_pattern_bounded():
    res = _run_child(_caller_sinks_child(), GUARDED_BUDGET)
    _assert_no_hang(res, "caller sinks")
    _assert_cases(
        res,
        {
            "stemmer_overlap": {"BOUNDED", "REFUSED"},
            "stemmer_nested": {"BOUNDED", "REFUSED"},
            "tokenizer_overlap": {"BOUNDED", "REFUSED"},
            "tokenizer_gaps": {"BOUNDED", "REFUSED"},
            "tagger_nested": {"BOUNDED", "REFUSED"},
            "featstruct_trailing_digits": {"BOUNDED"},
            "featstruct_interior_digits": {"BOUNDED"},
            "valuation_long_run": {"BOUNDED"},
            "chunk_overlap_tag": {"BOUNDED", "REFUSED"},
            "tgrep_overlap": {"BOUNDED", "REFUSED"},
        },
    )


# ==========================================================================
# Family 4: compile-time refusal (in-process -- refusal is instant, no hang)
# ==========================================================================

# Short, shallow sources whose counted repetitions the engine would expand into
# millions of copies at COMPILE time, plus over-long / over-nested sources. The
# match-time timeout runs too late for these, so ``check_pattern`` refuses them
# up front with a ``ValueError``.
_COMPILE_REFUSED = [
    pytest.param("a" * (MAX_PATTERN_LENGTH + 1), id="over_length"),
    pytest.param("(a)" * (MAX_PATTERN_LENGTH // 3 + 1), id="many_groups_over_length"),
    pytest.param(
        "(" * (MAX_NESTING_DEPTH + 1) + "a" + ")" * (MAX_NESTING_DEPTH + 1),
        id="deep_group_nesting",
    ),
    pytest.param("(" * (MAX_NESTING_DEPTH + 5), id="unbalanced_paren_flood"),
    pytest.param(
        "(?V1)" + "[" * (MAX_NESTING_DEPTH + 5) + "a" + "]" * (MAX_NESTING_DEPTH + 5),
        id="deep_char_class_nesting",
    ),
    pytest.param("a{%d}" % (MAX_REPEAT_PRODUCT + 1), id="bare_atom_count"),
    pytest.param("(ab){%d}" % (MAX_REPEAT_PRODUCT // 2 + 1), id="group_count"),
    pytest.param("((ab){1000}){1000}", id="nested_counts_multiply"),
    pytest.param("(?:(?:(?:a){1000}){1000}){1000}", id="triple_nested_counts"),
    pytest.param("a{500000,1000000}", id="range_minimum_expands"),
    pytest.param("a{1000000,}", id="open_range_minimum"),
    pytest.param("a{" + "9" * 20000 + "}", id="giant_count_digits"),
    pytest.param("|".join("tok%d" % i for i in range(200000)), id="huge_alternation"),
    pytest.param("(?:xyz){40000}", id="noncapturing_group_bomb"),
]


@pytest.mark.parametrize("pattern", _COMPILE_REFUSED)
def test_compile_time_bombs_refused(pattern):
    with pytest.raises(ValueError):
        redos.compile(pattern)
    # ``check_pattern`` alone (used by callers that compile with raw re/regex)
    # must refuse it too, so no bypass leaks around ``compile``.
    with pytest.raises(ValueError):
        redos.check_pattern(pattern)


# Shapes that LOOK bomb-like but are genuinely bounded -- the guard must not
# over-block them (a range from 0 does not expand its minimum; a moderate fixed
# count is fine; escaped / character-class parens are not group nesting).
_COMPILE_ALLOWED = [
    pytest.param("(a){0,1000000}", id="zero_range_no_expansion"),
    pytest.param("[a-z]{0,1000000}", id="class_zero_range"),
    pytest.param("(?:ab){2,50}", id="moderate_range"),
    pytest.param(r"(\d{1,3}\.){3}\d{1,3}", id="ip_like"),
    pytest.param("a" * MAX_PATTERN_LENGTH, id="at_length_limit"),
    pytest.param(
        "(" * MAX_NESTING_DEPTH + "a" + ")" * MAX_NESTING_DEPTH, id="at_nesting_limit"
    ),
    pytest.param(r"\(" * (MAX_NESTING_DEPTH + 50), id="escaped_parens_not_nesting"),
    pytest.param("[()]" * (MAX_NESTING_DEPTH + 50), id="class_parens_not_groups"),
    pytest.param("(?:a){50001}", id="just_over_half_limit"),
]


@pytest.mark.parametrize("pattern", _COMPILE_ALLOWED)
def test_bounded_lookalikes_still_compile(pattern):
    tp = redos.compile(pattern)
    assert isinstance(tp, redos.TimedPattern)
    redos.check_pattern(pattern)  # must not raise


# ==========================================================================
# Family 5: benign controls -- ordinary regexes still work, and fast
# ==========================================================================


class TestBenignStillWorks:
    def test_ordinary_patterns_match_correctly(self):
        assert redos.compile(r"\w+").findall("Good muffins here") == [
            "Good",
            "muffins",
            "here",
        ]
        assert redos.compile(r"\s+").split("a b  c") == ["a", "b", "c"]
        assert redos.compile(r"a").sub("X", "banana") == "bXnXnX"
        assert redos.compile(r"(?P<n>\d+)").search("x42").group("n") == "42"
        assert redos.fullmatch(r"[0-9]{3}-[0-9]{4}", "555-1234") is not None
        assert redos.compile(r"(ab|cd)+").search("abcdab").group() == "abcdab"

    def test_ordinary_patterns_are_fast(self):
        # A tight wall-clock bound: an ordinary pattern must resolve well inside a
        # second, so a regression that made it backtrack would fail here rather
        # than merely slow the suite.
        start = time.perf_counter()
        for _ in range(200):
            redos.compile(r"^-?[0-9]+(\.[0-9]+)?$").search("-3.14159")
        assert time.perf_counter() - start < 2.0

    def test_legitimate_large_but_safe_input_processes(self):
        # A large, benign corpus-sized input must still process linearly and fast.
        start = time.perf_counter()
        hits = redos.compile(r"\w+").findall("word " * 200000)
        assert len(hits) == 200000
        assert time.perf_counter() - start < 3.0

    def test_large_safe_split_is_linear(self):
        start = time.perf_counter()
        parts = redos.compile(r"\s+").split("a " * 100000)
        assert len(parts) == 100001
        assert time.perf_counter() - start < 3.0

    def test_benign_caller_sinks_still_correct(self):
        from nltk.stem import RegexpStemmer
        from nltk.tag import RegexpTagger
        from nltk.tokenize import RegexpTokenizer

        assert RegexpTokenizer(r"\w+").tokenize("hello world foo") == [
            "hello",
            "world",
            "foo",
        ]
        assert RegexpStemmer(r"ing$", min=4).stem("running") == "runn"
        assert RegexpTagger([(r"^\d+$", "CD"), (r".*", "NN")]).tag(["12", "cats"]) == [
            ("12", "CD"),
            ("cats", "NN"),
        ]


# ==========================================================================
# Teeth: prove a NEW candidate is genuinely hostile without the guard
# ==========================================================================


def test_teeth_stock_untimed_regex_hangs_on_counted_open_alternation():
    # ``(a|a){10,}$`` is in TIMEOUT_FAMILY: the ``regex`` optimiser does NOT
    # linearise it, so without the wall-clock timeout it hangs -- proving the
    # timeout (not the engine swap) is what bounds this shape.
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import regex; regex.compile(r'(a|a){10,}$').search('a'*80+'!'); print('x')",
            ],
            capture_output=True,
            text=True,
            timeout=STOCK_TEETH_TIMEOUT,
            env=env,
        )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
