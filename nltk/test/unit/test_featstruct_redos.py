"""Regression tests for the quadratic ReDoS in feature-structure variable
renaming (CWE-1333; CVE-2026-12919).

``nltk.featstruct._rename_variable`` strips a trailing run of digits from a
variable name with ``re.sub(r"\\d+$", "", var.name)``. The greedy ``\\d+`` made a
name with a long run of digits not at the end (e.g. ``x000...0z``) re-scan the
run from every position, which is quadratic in the run length -- so a single
untrusted feature structure renamed (or unified, which renames by default) could
pin a CPU core. A ``(?<!\\d)`` lookbehind now lets the run match only at its
start, making the substitution linear while leaving the result unchanged.

The "must stay linear" test runs in a spawned process with a hard timeout, and
the worker reports via its exit code (no queue/thread, so it is robust on
free-threaded builds), so a regression to the quadratic pattern cannot hang the
suite.
"""

import multiprocessing
import os

from nltk.featstruct import FeatStruct, _rename_variable
from nltk.sem.logic import Variable


def test_rename_variable_strips_trailing_digits():
    # The trailing-number stripping (and fresh-suffix) behaviour is unchanged.
    assert _rename_variable(Variable("x12"), set()) == Variable("x2")
    assert _rename_variable(Variable("foo3"), set()) == Variable("foo2")
    assert _rename_variable(Variable("x"), set()) == Variable("x2")
    # A digit run that is not at the end is not stripped (ends in 'z').
    assert _rename_variable(Variable("x000z"), set()) == Variable("x000z2")
    # Only the trailing run is stripped.
    assert _rename_variable(Variable("x1y23"), set()) == Variable("x1y2")
    # Fresh suffix avoids clashes with used_vars.
    assert _rename_variable(Variable("x"), {Variable("x2")}) == Variable("x3")


def test_rename_and_unify_preserved():
    assert str(FeatStruct("[a=?x, b=?y]").rename_variables()) == str(
        FeatStruct("[a=?x2, b=?y2]")
    )
    unified = FeatStruct("[a=?p]").unify(FeatStruct("[b=?q]"))
    assert unified is not None
    assert unified["a"] == Variable("?p")
    assert unified["b"] == Variable("?q")


_TIMEOUT = 20
# A variable name with a long run of digits that is not at the end. The pre-fix
# greedy ``\d+`` made renaming this quadratic (~tens of seconds at this size);
# the fix makes it linear (~milliseconds). It is CPU-only (a ~0.2 MB string), so
# there is no OOM risk.
_EVIL = "[a=?x" + "0" * 200_000 + "z]"


def _rename_worker():
    # Renaming this (valid) feature structure must actually complete quickly.
    # Exit non-zero on any failure so the parent assertion fails -- otherwise a
    # swallowed exception (e.g. parsing breaking before the rename runs) would
    # let the test pass without exercising the vulnerable rename path.
    try:
        FeatStruct(_EVIL).rename_variables()
        os._exit(0)
    except BaseException:
        os._exit(3)


def test_long_digit_run_renames_in_linear_time():
    """A long digit-run variable name must rename in linear time (not ReDoS)."""
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_rename_worker)
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "feature-structure renaming did not finish in time -> quadratic ReDoS"
        )
    assert proc.exitcode == 0, f"worker failed (exit code {proc.exitcode})"
