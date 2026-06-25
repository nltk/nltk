"""Regression tests for unbounded proof search in NLTK's in-process first-order
theorem provers ``ResolutionProver`` and ``TableauProver`` (CWE-400 / CWE-674).

Both provers expose a public ``prove()`` that historically ran the search with
*no* resource bound:

* ``ResolutionProver`` saturates an ever-growing clause list; for a satisfiable
  goal (one that does not follow) the loop derives resolvents forever and pins a
  CPU core -- ``prove()`` never returns. The cost of a single unification grows
  as clauses accumulate literals, so a clause/step count does not bound the wall
  time; the search is now bounded by a configurable wall-clock ``TIMEOUT``
  (mirroring ``nltk.inference.Prover9``), returning ``False`` when it elapses.
* ``TableauProver`` expands an infinite tableau for a serial relation such as
  ``all x.exists y.succ(x,y)``; because ``_assume_false`` is ``False`` the
  resulting ``RecursionError`` was re-raised straight out of ``prove()`` and
  crashed the caller. Expansion depth is now bounded by ``MAX_TABLEAU_DEPTH``
  (kept below Python's recursion limit, so the branch is simply reported
  unclosed), with a wall-clock ``TIMEOUT`` as a backstop for tableaux that fan
  out without growing deep.

The "must terminate" tests run the malicious proof in a separate process (spawn)
with a hard deadline and ``terminate()`` on overrun, so a regression to an
unbounded search cannot keep burning CPU for the rest of the suite, and any
exception in the worker (e.g. a re-raised ``RecursionError``) is propagated back
to the assertions instead of crashing the runner.
"""

import multiprocessing
import queue

from nltk.inference import (
    ResolutionProverCommand,
    TableauProverCommand,
)
from nltk.inference.resolution import ResolutionProver
from nltk.inference.tableau import TableauProver
from nltk.sem import Expression

read = Expression.fromstring

# A benign goal that genuinely follows from its assumptions: both provers must
# still prove it (the resource bounds must not change sound results).
_BENIGN_GOAL = read("mortal(socrates)")
_BENIGN_ASSUMPTIONS = [read("all x.(man(x) -> mortal(x))"), read("man(socrates)")]

# Tight bound used by the malicious-input workers so the test is quick; the
# shipped default is far larger. The worker is hard-killed only if the bound
# fails to fire, which is the regression we are guarding against.
_WORKER_TIMEOUT = 2
# Hard deadline for the whole worker (process startup + import + bounded search).
# Generous vs. the ~few seconds a correctly-bounded search takes, but far below
# the unbounded cost, so a regression fails fast and cleanly.
_DEADLINE = 30


def _resolution_attack_worker(result_q, timeout):
    """Run an unbounded resolution search (transitive closure of a chain)."""
    try:
        prover = ResolutionProver()
        prover.TIMEOUT = timeout
        # A transitivity rule over a 40-node chain: the closure keeps deriving
        # ever-larger resolvents, so without a bound this never returns.
        assumptions = [read("all x.all y.all z.((R(x,y) & R(y,z)) -> R(x,z))")] + [
            read(f"R(n{k},n{k + 1})") for k in range(39)
        ]
        result = ResolutionProverCommand(
            read("G(z)"), assumptions, prover=prover
        ).prove()
        result_q.put(("ok", result))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _tableau_attack_worker(result_q):
    """Run an infinite-tableau search (serial relation) with shipped defaults."""
    try:
        # all x.exists y.succ(x,y) mints a fresh witness forever; previously this
        # escaped prove() as an uncaught RecursionError.
        assumptions = [read("all x.exists y.succ(x,y)"), read("succ(a,a)")]
        result = TableauProverCommand(read("loop(a)"), assumptions).prove()
        result_q.put(("ok", result))
    except BaseException as exc:
        result_q.put(("error", repr(exc)))


def _run_in_process(target, args=()):
    """Run ``target(result_q, *args)`` in a spawned process with a deadline.

    Returns ``(finished, status, payload)``. If the worker overruns
    ``_DEADLINE`` it is terminated (no lingering CPU) and ``finished`` is
    ``False``.
    """
    ctx = multiprocessing.get_context("spawn")
    result_q = ctx.Queue()
    proc = ctx.Process(target=target, args=(result_q, *args))
    proc.start()
    proc.join(_DEADLINE)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return False, None, None
    try:
        status, payload = result_q.get_nowait()
    except queue.Empty:
        return True, "error", "worker produced no result"
    return True, status, payload


def test_resolution_benign_proof_preserved():
    """The wall-clock bound must not change a sound, quick resolution proof."""
    assert ResolutionProverCommand(_BENIGN_GOAL, _BENIGN_ASSUMPTIONS).prove() is True


def test_tableau_benign_proof_preserved():
    """The depth/time bounds must not change a sound, quick tableau proof."""
    assert TableauProverCommand(_BENIGN_GOAL, _BENIGN_ASSUMPTIONS).prove() is True


def test_resolution_unbounded_search_now_terminates():
    """A satisfiable goal must time out and return False, not hang forever."""
    finished, status, payload = _run_in_process(
        _resolution_attack_worker, (_WORKER_TIMEOUT,)
    )
    assert finished, "ResolutionProver.prove() did not terminate (unbounded search)"
    assert status == "ok", f"worker raised: {payload}"
    assert payload is False


def test_tableau_infinite_tableau_now_terminates():
    """An infinite tableau must return False, not escape as a RecursionError."""
    finished, status, payload = _run_in_process(_tableau_attack_worker)
    assert finished, "TableauProver.prove() did not terminate (infinite tableau)"
    # Previously this propagated an uncaught RecursionError out of prove().
    assert status == "ok", f"worker raised: {payload}"
    assert payload is False


def test_tableau_timeout_backstop_returns_false(monkeypatch):
    """The wall-clock backstop reports the goal unproved once the deadline passes.

    Driven by a fake clock so it is deterministic and needs no deep recursion:
    the deadline is computed from the first reading, and the first expansion step
    sees a clock already far past it.
    """
    from nltk.inference import tableau

    readings = iter([1000.0])

    def fake_monotonic():
        try:
            return next(readings)
        except StopIteration:
            return 1e12  # everything after the deadline computation is "later"

    monkeypatch.setattr(tableau.time, "monotonic", fake_monotonic)
    assumptions = [read("all x.exists y.succ(x,y)"), read("succ(a,a)")]
    assert TableauProverCommand(read("loop(a)"), assumptions).prove() is False


def test_resource_bounds_are_tunable_with_safe_defaults():
    """Both provers expose tunable bounds with sane, documented defaults."""
    assert ResolutionProver.TIMEOUT == 60
    assert TableauProver.TIMEOUT == 60
    assert TableauProver.MAX_TABLEAU_DEPTH == 200

    # TIMEOUT == 0 disables the wall-clock bound (the original behaviour); a
    # quick, sound proof must still succeed with the limit turned off.
    prover = ResolutionProver()
    prover.TIMEOUT = 0
    assert (
        ResolutionProverCommand(
            _BENIGN_GOAL, _BENIGN_ASSUMPTIONS, prover=prover
        ).prove()
        is True
    )
