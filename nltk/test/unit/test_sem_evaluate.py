"""Regression tests for the combinatorial-blowup DoS in nltk.sem model
evaluation (CWE-770; CVE-2026-12840).

A formula with k nested quantifiers/lambdas makes ``Model.satisfy`` do
O(|domain| ** k) work, and k comes entirely from the (untrusted) formula. The
cost is now bounded by ``Model.MAX_SATISFY_OPERATIONS`` before the recursion can
blow up. These tests confirm the bound refuses deeply-nested formulas while
legitimate shallow ones still evaluate.

The "must not hang" test runs in a spawned process with a hard timeout so a
regression (running the unbounded O(|domain| ** k) loop) cannot hang the suite.
"""

import multiprocessing
import queue

from nltk.sem import Assignment, Model, Valuation
from nltk.sem.evaluate import Error, _max_binder_depth
from nltk.sem.logic import Expression


def _model():
    dom = {"a", "b"}
    val = Valuation([("P", {("a",)}), ("R", {("a", "b")})])
    return Model(dom, val), Assignment(dom)


def test_max_binder_depth():
    p = Expression.fromstring
    assert _max_binder_depth(p("P(x)")) == 0
    assert _max_binder_depth(p("all x.P(x)")) == 1
    assert _max_binder_depth(p("all x.all y.R(x,y)")) == 2
    assert _max_binder_depth(p("all x.(P(x) & exists y.R(x,y))")) == 2
    assert _max_binder_depth(p("exists x.-all y.R(x,y)")) == 2


def test_legitimate_formulas_still_evaluate():
    m, g = _model()
    assert m.evaluate("all x.(x = x)", g) is True
    assert m.evaluate("exists x.P(x)", g) is True
    assert m.evaluate("all x.exists y.R(x,y)", g) is False


def test_shallow_formula_within_bound_allowed():
    # depth 5 over a domain of 10 -> 1e5 < MAX_SATISFY_OPERATIONS (1e6): allowed.
    dom = set("abcdefghij")
    m = Model(dom, Valuation([("P", {("a",)})]))
    g = Assignment(dom)
    f = "all x0.all x1.all x2.all x3.all x4.(x0 = x0)"
    assert m.evaluate(f, g) is True


_TIMEOUT = 15


def _eval_worker(result_q):
    try:
        dom = set("abcdefghij")  # |domain| = 10
        m = Model(dom, Valuation([("P", {("a",)})]))
        g = Assignment(dom)
        # 9 nested quantifiers -> 10**9 satisfaction checks if unbounded.
        f = "".join("all x%d." % i for i in range(9)) + "(x0 = x0)"
        try:
            m.evaluate(f, g)
            result_q.put(("ok", "evaluated"))
        except Error:
            result_q.put(("ok", "refused"))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _run_in_process(target):
    ctx = multiprocessing.get_context("spawn")
    result_q = ctx.Queue()
    proc = ctx.Process(target=target, args=(result_q,))
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return False, None, None
    try:
        status, payload = result_q.get_nowait()
    except queue.Empty:
        return True, "error", "worker produced no result"
    return True, status, payload


def test_deeply_nested_formula_is_refused_not_evaluated():
    """A deeply-nested formula must be refused, not run as O(|domain| ** k)."""
    finished, status, value = _run_in_process(_eval_worker)
    assert (
        finished
    ), "Model.evaluate ran an unbounded O(|domain| ** k) computation (DoS)"
    assert status == "ok", f"worker raised: {value}"
    assert value == "refused"
