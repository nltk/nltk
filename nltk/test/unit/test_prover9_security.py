# Natural Language Toolkit: Prover9 input-injection guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk.inference.prover9 builds the Prover9 input by interpolating each
converted logic formula into a ``formulas(...)`` list. A crafted term carrying a
bare period, a newline, a NUL, or a leading list keyword could close the list
early and inject extra Prover9 directives such as ``end_of_list.``
(CVE-2026-14709). These tests pin the local guard and confirm prover9_input (and
therefore mace, which reuses it) routes through it, while genuine formulas still
convert."""

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
        "end_of_list_marker(x)",  # reserved word only as a strict prefix
        "formulasize(y)",
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
        "end_of_list",  # formula IS the list terminator
        "formulas(goals)",  # list opener
        "clauses(sos)",  # clause-list opener
        "end_of_list(x)",  # leading reserved keyword
        "p(x)\x00drop",  # NUL
        "  end_of_list",  # leading whitespace does not launder it
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


def test_prover9_input_rejects_crafted_expression():
    # A hand-built Expression whose str() injects directives is stopped before it
    # can reach the Prover9 stdin (Expression.fromstring never yields such text,
    # so this is the defense-in-depth path).
    class Evil:
        def simplify(self):
            return self

        def __str__(self):
            return "p(x).\nend_of_list.\nformulas(goals).\n exploit(y)"

    with pytest.raises(ValueError, match="inject"):
        Prover9Parent.prover9_input(Prover9(), Evil(), [])


def test_fromstring_path_is_not_reachable_for_injection():
    # Real inputs go through Expression.fromstring, which only produces identifier
    # atoms, so a legitimate parse never trips the guard.
    for text in ["man(socrates)", "all x.(walk(x) -> move(x))", "-(P(a) & Q(b))"]:
        _assert_prover9_safe(convert_to_prover9(read(text)))
