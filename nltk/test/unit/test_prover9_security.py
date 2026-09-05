# Natural Language Toolkit: Prover9 input-injection guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk.inference.prover9 builds the Prover9 input by interpolating each converted
logic formula into a ``formulas(...)`` list. A crafted term carrying a bare
period, a control character, a NUL, or a leading list keyword could close the
list early and inject extra Prover9 directives such as ``end_of_list.``
(CVE-2026-14709). These tests pin the local guard and confirm ``prover9_input``
(and therefore Mace, which reuses it) routes through it, while genuine formulas
still convert.
"""

import pytest

from nltk.inference.prover9 import (
    Prover9,
    Prover9Parent,
    _assert_prover9_safe,
    convert_to_prover9,
)
from nltk.sem.logic import Expression

read = Expression.fromstring


@pytest.mark.parametrize(
    "formula",
    [
        "man(socrates)",
        "walk(john)",
        "(P(x) & Q(y))",
        "-(mortal(x))",
        "exists x see(x,y)",
        "all x (man(x) -> mortal(x))",
        "(P(a) <-> Q(b))",
        "end_of_list_marker(x)",  # reserved word only as a strict prefix
        "formulasize(y)",  # 'formulas' is only a prefix here
        "clauses_of(x)",  # 'clauses' is only a prefix here
        "p(x)\tq(y)",  # a tab is ordinary whitespace, not a line break
        "(a = b)",  # equality is legitimate Prover9 syntax
        "all x exists y (loves(x,y) & -hates(y,x))",  # connectives, quantifiers
    ],
)
def test_genuine_formulas_pass(formula):
    assert _assert_prover9_safe(formula) == formula


@pytest.mark.parametrize(
    "formula",
    [
        "p(x). end_of_list. formulas(goals). q(x)",  # bare period breakout
        "p(x)\nend_of_list.\nformulas(goals).\nq(x)",  # newline breakout
        "p(x)\r\nend_of_list.",  # CRLF breakout
        "p(x)\rend_of_list.",  # bare CR
        "end_of_list",  # formula IS the list terminator
        "formulas(goals)",  # list opener
        "clauses(sos)",  # clause-list opener
        "end_of_list(x)",  # leading reserved keyword
        "p(x)\x00drop",  # NUL
        "p(x)\x0bq",  # vertical tab (control)
        "p(x)\x0cq",  # form feed (control)
        "p(x)\x1fq",  # unit separator (control)
        "p(x)\x7fq",  # DEL (control)
        "  end_of_list",  # leading whitespace does not launder it
        "\tformulas(goals)",  # leading tab does not launder a list opener
        "p(a) % x",  # '%' comments out the appended period, merging formulas
        "p(a)%end_of_list",  # comment char plus a directive
        "p(a) # answer(evil)",  # '#' injects a Prover9 answer/label attribute
        "p(a)#label(spoof)",  # '#' label char
    ],
)
def test_injection_formulas_refused(formula):
    with pytest.raises(ValueError, match="inject"):
        _assert_prover9_safe(formula)


def test_prover9_input_builds_and_guards():
    p = Prover9()
    good = p.prover9_input(read("man(socrates)"), [read("all x.(man(x) -> mortal(x))")])
    assert "formulas(assumptions)." in good
    assert "end_of_list." in good
    assert "man(socrates)" in good


def _evil(payload):
    class Evil:
        def simplify(self):
            return self

        def __str__(self):
            return payload

    return Evil()


@pytest.mark.parametrize(
    "payload",
    [
        "p(x).\nend_of_list.\nformulas(goals).\n exploit(y)",
        "p(x)\x00",
        "end_of_list",
        "p(x)\x0cq",
    ],
)
def test_prover9_input_rejects_crafted_expression_as_goal(payload):
    # A hand-built Expression whose str() injects directives is stopped before it
    # can reach the Prover9 stdin (Expression.fromstring never yields such text,
    # so this is the defence-in-depth path). Exercised as the goal argument.
    with pytest.raises(ValueError, match="inject"):
        Prover9Parent.prover9_input(Prover9(), _evil(payload), [])


def test_prover9_input_rejects_crafted_expression_in_assumptions():
    # And as an assumption (the loop path), so both interpolation sites are guarded.
    with pytest.raises(ValueError, match="inject"):
        Prover9Parent.prover9_input(
            Prover9(), read("man(socrates)"), [_evil("p(x).\nend_of_list.")]
        )


def test_mace_reuses_the_guarded_prover9_input():
    # Mace builds its input through the same Prover9Parent.prover9_input, so the
    # guard protects it too.
    from nltk.inference.mace import Mace

    with pytest.raises(ValueError, match="inject"):
        Mace().prover9_input(_evil("p(x).\nend_of_list.\nassign(max_seconds,0)"), [])


def test_fromstring_path_is_not_reachable_for_injection():
    # Real inputs go through Expression.fromstring, which only produces identifier
    # atoms, so a legitimate parse never trips the guard.
    for text in ["man(socrates)", "all x.(walk(x) -> move(x))", "-(P(a) & Q(b))"]:
        _assert_prover9_safe(convert_to_prover9(read(text)))


# --- Resource-bound validation (max_seconds / end_size): CWE-400 + type safety --
# The timeout/end_size are interpolated into ``assign(max_seconds, %d)``. The
# ``%d`` blocks injection, but a negative value is undefined to the binary and a
# non-int raises at format time; both are refused up front (0 is the documented
# "no timeout", the caller's own DoS choice).


@pytest.mark.parametrize(
    "bad", [-1, -60, "60", "0). formulas(goals)", 1.5, 3.0, True, False, None, []]
)
def test_safe_seconds_rejects_non_nonnegative_int(bad):
    from nltk.inference.prover9 import _safe_seconds

    with pytest.raises(ValueError, match="non-negative integer"):
        _safe_seconds(bad)


@pytest.mark.parametrize("good", [0, 1, 60, 3600])
def test_safe_seconds_accepts_nonnegative_int(good):
    from nltk.inference.prover9 import _safe_seconds

    assert _safe_seconds(good) == good


def test_prover9_rejects_bad_timeout_before_spawn():
    # A bad timeout is caught before the binary is even located, so there is no
    # spawn and the caller gets a clear ValueError rather than a later TypeError.
    with pytest.raises(ValueError, match="non-negative integer"):
        Prover9(timeout=-5)._call_prover9("formulas(goals).\nend_of_list.\n")


def test_mace_rejects_bad_end_size_before_spawn():
    from nltk.inference.mace import Mace

    builder = Mace()
    builder._end_size = -1
    with pytest.raises(ValueError, match="non-negative integer"):
        builder._call_mace4("formulas(assumptions).\nend_of_list.\n")
