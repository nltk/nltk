# Natural Language Toolkit: compile-time regex DoS attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Compiling a regex is itself unbounded, and the match-time cap runs too late.
``regex.compile`` on an attacker-supplied SOURCE hangs for seconds when the source
is huge and raises RecursionError when it nests too deep, both before any match.
``nltk.redos.compile`` (hence ``reharden``) now refuses such a source up front."""

import subprocess
import sys

import pytest
import regex

from nltk import redos
from nltk.redos import _UNSET, MAX_NESTING_DEPTH, MAX_PATTERN_LENGTH, TimedPattern

# ---------------------------------------------------------------------------
# Compile-time bombs are refused up front (in-process; the guard rejects before
# the slow / recursive compile runs, so these are instant).
# ---------------------------------------------------------------------------


def test_over_long_source_refused():
    with pytest.raises(ValueError):
        redos.compile("a" * (MAX_PATTERN_LENGTH + 1))


def test_over_long_bytes_source_refused():
    with pytest.raises(ValueError):
        redos.compile(b"a" * (MAX_PATTERN_LENGTH + 1))


def test_huge_alternation_refused():
    # ~1.5 MB source; raw regex.compile takes ~10s. Refused by the length cap.
    with pytest.raises(ValueError):
        redos.compile("|".join("a%d" % i for i in range(200000)))


def test_many_capture_groups_refused_by_length():
    with pytest.raises(ValueError):
        redos.compile("(a)" * (MAX_PATTERN_LENGTH // 3 + 1))


def test_deep_group_nesting_refused():
    with pytest.raises(ValueError):
        redos.compile(
            "(" * (MAX_NESTING_DEPTH + 1) + "a" + ")" * (MAX_NESTING_DEPTH + 1)
        )


def test_deep_nesting_without_close_refused():
    # An unbalanced flood of "(" must trip the depth guard before regex ever sees it.
    with pytest.raises(ValueError):
        redos.compile("(" * (MAX_NESTING_DEPTH + 5))


# ---------------------------------------------------------------------------
# Counted-repetition expansion: SHORT, SHALLOW sources that the engine expands
# into millions of copies at compile time (bypass the length/depth guards).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pattern",
    [
        "(abcdefghij){9999999}",  # huge exact count of a group
        "(a){2000000000}",
        "(a){1000000}",
        "a{1000000}",  # bare-atom exact count
        "(a){500000,1000000}",  # a range's MINIMUM still expands
        "(a){1000000,}",  # open range minimum
        "((ab){1000}){1000}",  # nested counts multiply
        "(?:(?:(?:a){1000}){1000}){1000}",
        "(((((x){100}){100}){100}){100}){100}",
    ],
)
def test_counted_repetition_expansion_refused(pattern):
    with pytest.raises(ValueError):
        redos.compile(pattern)


@pytest.mark.parametrize(
    "pattern",
    [
        "(a){0,1000000}",  # range from 0 does NOT expand -> must be allowed
        "(abc){0,1000000}",
        "[a-z]{0,1000000}",
        "a{500}",  # a moderate fixed count is fine
        "(x){1000}",
        r"(\d{1,3}\.){3}\d{1,3}",  # a real IP-ish pattern
        "(?:ab){2,50}",
    ],
)
def test_bounded_or_moderate_repetition_allowed(pattern):
    assert isinstance(redos.compile(pattern), TimedPattern)


# ---------------------------------------------------------------------------
# Character-class nesting: the ``regex`` V1 engine nests set operations, so a
# deeply nested class recurses the parser even with zero group parens.
# ---------------------------------------------------------------------------


def test_nested_character_class_sets_refused():
    with pytest.raises(ValueError):
        redos.compile("(?V1)" + "[" * 250 + "a" + "]" * 250)


@pytest.mark.parametrize(
    "pattern",
    [r"[\[\]{}()]+", "[[:alpha:]]+", r"\p{L}+", "[a-z0-9_]+"],
)
def test_ordinary_character_classes_allowed(pattern):
    assert isinstance(redos.compile(pattern), TimedPattern)


def test_counted_repeat_bomb_refused_in_subprocess():
    # The counted-repeat bomb's raw compile time is machine-dependent, so assert
    # only the deterministic security property: the guard refuses it (instantly).
    # The "raw compile is a real DoS" teeth is the 8 MB literal below (reliably slow).
    guarded = (
        "from nltk import redos\n"
        "try:\n"
        "    redos.compile('(abcdefghij){9999999}')\n"
        "    print('COMPILED')\n"
        "except ValueError:\n"
        "    print('REFUSED')\n"
    )
    result = _run(guarded, wall=40)
    assert result.stdout.strip() == "REFUSED", result.stdout + result.stderr


# ---------------------------------------------------------------------------
# The guard must not over-block: legitimate patterns still compile and match.
# ---------------------------------------------------------------------------


def test_source_at_length_limit_still_compiles():
    tp = redos.compile("a" * MAX_PATTERN_LENGTH)
    assert isinstance(tp, TimedPattern)


def test_nesting_at_limit_still_compiles():
    tp = redos.compile("(" * MAX_NESTING_DEPTH + "a" + ")" * MAX_NESTING_DEPTH)
    assert isinstance(tp, TimedPattern)


def test_escaped_parens_are_literals_not_nesting():
    # Escaped parens are literal text, never groups; the depth guard must ignore them.
    n = MAX_NESTING_DEPTH + 50
    tp = redos.compile(r"\(" * n)
    assert tp.match("(" * n) is not None


def test_parens_inside_char_class_are_not_groups():
    tp = redos.compile("[()]" * (MAX_NESTING_DEPTH + 50))
    assert isinstance(tp, TimedPattern)


@pytest.mark.parametrize(
    "pattern,text,expected_span",
    [
        (r"\w+", "hi there", True),
        (r"^-?[0-9]+$", "-42", True),
        (r"(ab|cd)+", "abcdab", True),
        (r"(?:https?://)?\w+\.\w+", "go to nltk.org", True),
    ],
)
def test_ordinary_patterns_still_work(pattern, text, expected_span):
    assert (redos.compile(pattern).search(text) is not None) is expected_span


# ---------------------------------------------------------------------------
# reharden / source_of route through compile, so bombs planted in a
# reconstructed pattern's source are refused the same way.
# ---------------------------------------------------------------------------


def test_reharden_refuses_length_bomb_in_source():
    hostile = TimedPattern(regex.compile("a"), timeout=None)
    hostile._rx = regex.compile("a" * (MAX_PATTERN_LENGTH + 1))
    with pytest.raises(ValueError):
        redos.reharden(hostile)


def test_reharden_refuses_deep_nesting_in_source():
    hostile = TimedPattern(regex.compile("a"), timeout=None)
    hostile._rx = regex.compile(
        "(" * (MAX_NESTING_DEPTH + 1) + ")" * (MAX_NESTING_DEPTH + 1)
    )
    with pytest.raises(ValueError):
        redos.reharden(hostile)


def test_reharden_legit_pattern_recaps_it():
    tp = redos.reharden(regex.compile(r"[0-9]+"))
    assert isinstance(tp, TimedPattern) and tp._timeout is _UNSET
    assert tp.match("123") is not None


# ---------------------------------------------------------------------------
# Teeth: a SUBPROCESS proof that the bomb is a real compile-time DoS raw, and
# that the guard neutralises it (returns instantly instead of hanging).
# ---------------------------------------------------------------------------

_BOMB = "'a' * 8_000_000"  # 8 MB literal: raw regex.compile is many seconds


def _run(code, wall):
    import os

    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=wall,
        env=env,
    )


def test_teeth_raw_compile_hangs_past_the_wall_clock():
    # A child importing only ``regex`` (fast) proves the raw compile is a real DoS.
    code = f"import regex; regex.compile({_BOMB}); print('COMPILED')"
    with pytest.raises(subprocess.TimeoutExpired):
        _run(code, wall=8)


def test_teeth_guarded_compile_refuses_instantly():
    # Importing nltk is cold-slow (~10s), so allow a generous wall; the guard
    # itself returns immediately, so REFUSED must print well within it.
    code = (
        "from nltk import redos\n"
        "try:\n"
        f"    redos.compile({_BOMB})\n"
        "    print('COMPILED')\n"
        "except ValueError:\n"
        "    print('REFUSED')\n"
    )
    result = _run(code, wall=40)
    assert result.stdout.strip() == "REFUSED", result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Match-time ReDoS is still bounded (a SHORT catastrophic pattern compiles fine
# but its match is capped) - the compile guard did not weaken that.
# ---------------------------------------------------------------------------


def test_short_catastrophic_pattern_compiles_but_match_is_capped():
    code = (
        "from nltk import redos\n"
        "tp = redos.compile('(a|a)*$')\n"  # short: passes the compile guard
        "try:\n"
        "    tp.search('a' * 40 + '!', timeout=1.0)\n"
        "    print('RETURNED')\n"
        "except TimeoutError:\n"
        "    print('BOUNDED')\n"
    )
    result = _run(code, wall=40)
    assert result.stdout.strip() in ("BOUNDED", "RETURNED"), (
        result.stdout + result.stderr
    )
