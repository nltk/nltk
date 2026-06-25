"""Regression test for the exponential beta-reduction DoS in
``nltk.sem.logic.ApplicationExpression.simplify`` (CWE-400).

Beta reduction substitutes the argument into the lambda body; when the body
references its bound variable more than once the argument is duplicated, so a
short expression built from nested duplicating lambdas (``(\\Y.(Y & Y))``)
reduces to an exponentially large normal form and exhausts CPU and memory.
``simplify`` now refuses with a ``ValueError`` once a single reduction's result
exceeds ``MAX_SIMPLIFY_SIZE`` subexpressions; ordinary reductions are unchanged.
"""

import multiprocessing
import os

from nltk.sem import Expression
from nltk.sem.logic import MAX_SIMPLIFY_SIZE, _exceeds_size

_DOUBLER = r"(\Y.(Y & Y))"


def _nest(k):
    """k nested doublers applied to P(a) (reduces to 2**k copies of P(a))."""
    expr = "P(a)"
    for _ in range(k):
        expr = f"{_DOUBLER}({expr})"
    return expr


def test_simplify_preserves_benign_reductions():
    """Ordinary beta reductions are unchanged."""
    assert Expression.fromstring(r"(\x.P(x))(a)").simplify() == Expression.fromstring(
        "P(a)"
    )
    assert Expression.fromstring(
        f"{_DOUBLER}(P(a))"
    ).simplify() == Expression.fromstring("P(a) & P(a)")
    # A non-application is returned untouched.
    formula = r"\x.(P(x) -> Q(x))"
    assert Expression.fromstring(formula).simplify() == Expression.fromstring(formula)


def test_simplify_under_cap_duplicates_as_before():
    """Under the cap, a duplicating reduction still doubles (2**k copies)."""
    result = Expression.fromstring(_nest(5)).simplify()
    assert str(result).count("P(a)") == 2**5


def test_max_simplify_size_is_configurable():
    """The cap is a positive int and the size check short-circuits correctly."""
    assert isinstance(MAX_SIMPLIFY_SIZE, int) and MAX_SIMPLIFY_SIZE > 0
    small = Expression.fromstring("P(a) & Q(b)")
    assert _exceeds_size(small, 100) is False
    assert _exceeds_size(small, 2) is True


def _blowup_worker():
    """Simplify a huge nested-doubler expression; exit 0 if the cap fires."""
    try:
        Expression.fromstring(_nest(100)).simplify()
        os._exit(1)  # completed without the cap firing -> blow-up not bounded
    except ValueError:
        os._exit(0)  # expected: the size cap refused the reduction
    except BaseException:
        os._exit(3)


def test_simplify_bounds_exponential_blowup():
    """A nested-doubler expression must be refused quickly, not blow up.

    Run in a spawned process with a hard deadline: with the cap the reduction
    raises almost immediately, while the unbounded version needs exponential CPU
    and memory at this size, so a regression is terminated instead of OOM-killing
    or hanging the suite.
    """
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_blowup_worker)
    proc.start()
    proc.join(30)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "simplify() did not terminate: exponential beta-reduction regressed"
        )
    assert (
        proc.exitcode == 0
    ), f"expected a ValueError from the size cap (exit {proc.exitcode})"
