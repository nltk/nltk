"""Regression tests for unbounded recursion in the logic parser (CWE-674).

`LogicParser` is a recursive-descent parser: each nested sub-expression recurses
through `process_next_expression`. Deeply nested input would otherwise recurse
until Python raised an uncaught `RecursionError`, crashing the caller. The parser
now caps the nesting depth at `LogicParser.MAX_PARSE_DEPTH` and raises a normal
`LogicalExpressionException` instead.
"""

import pytest

from nltk.sem.logic import Expression, LogicalExpressionException, LogicParser


def test_deeply_nested_expression_raises_clean_error():
    """A pathologically deep expression raises a clean parse error, not an
    uncaught RecursionError (uncontrolled recursion, CWE-674)."""
    # If an uncaught RecursionError were raised instead, pytest.raises would not
    # catch it and the test would fail with the unexpected exception.
    with pytest.raises(LogicalExpressionException):
        Expression.fromstring("-" * 5000 + "p")  # 5000 nested negations


def test_normal_expressions_still_parse():
    """Ordinary expressions are unaffected by the depth cap."""
    for s in [
        "exists x.(P(x) & Q(x))",
        "all x.(man(x) -> mortal(x))",
        "\\x.(P(x))(a)",
        "-(p & q)",
        "P(a,b,c)",
    ]:
        assert str(Expression.fromstring(s))  # parses without error


def test_depth_cap_is_configurable_and_enforced():
    """Nesting up to the cap parses; nesting beyond it raises a clean error."""
    saved = LogicParser.MAX_PARSE_DEPTH
    LogicParser.MAX_PARSE_DEPTH = 20
    try:
        # 19 nested negations: under the cap, parses fine.
        assert str(Expression.fromstring("-" * 19 + "p"))
        # 21 nested negations: over the cap, clean LogicalExpressionException.
        with pytest.raises(LogicalExpressionException):
            Expression.fromstring("-" * 21 + "p")
    finally:
        LogicParser.MAX_PARSE_DEPTH = saved
