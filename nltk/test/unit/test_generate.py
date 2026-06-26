"""Regression tests for the unbounded-enumeration DoS in
``nltk.parse.generate.generate`` (CWE-400).

A recursive grammar can derive an exponential (doubly-exponential for a
self-embedding rule) number of sentences. With the default ``depth`` and no
``n`` limit, ``generate`` over a 15-byte grammar such as ``S -> S S | 'a'``
never terminates (it hangs producing even the first sentence) or exhausts
memory. The number of derivation-expansion steps is now bounded by
``MAX_GENERATE_OPERATIONS``; once exceeded, generation raises ``ValueError``.

The "must not hang" test runs in a spawned process with a hard timeout so a
regression (running the unbounded enumeration) cannot hang/OOM the suite.
"""

import multiprocessing
import queue

import pytest

from nltk import CFG
from nltk.parse import generate as generate_mod
from nltk.parse.generate import MAX_GENERATE_OPERATIONS, demo_grammar, generate


def test_max_generate_operations_is_a_finite_positive_int():
    assert isinstance(MAX_GENERATE_OPERATIONS, int)
    assert MAX_GENERATE_OPERATIONS > 0


def test_behaviour_preserved_for_finite_grammars():
    grammar = CFG.fromstring(demo_grammar)
    # The values asserted in generate.doctest must be unchanged.
    assert len(list(generate(grammar, n=10))) == 10
    assert len(list(generate(grammar, depth=3))) == 0
    assert len(list(generate(grammar, depth=4))) == 6
    assert len(list(generate(grammar, depth=5))) == 42
    assert len(list(generate(grammar, depth=6))) == 114
    # Default depth on a (non-recursive) grammar still enumerates everything.
    assert len(list(generate(grammar))) == 114
    # Empty strings / empty productions (grammar.doctest) still work.
    g2 = CFG.fromstring("S -> A B\nA -> 'a'\nB -> 'b' | ''")
    assert list(generate(g2)) == [["a", "b"], ["a", ""]]


def test_n_zero_returns_no_sentences():
    # n is the maximum number of sentences; n=0 must return none, not be
    # treated as "no limit". Holds even for a recursive grammar (nothing is
    # enumerated, so no budget error).
    grammar = CFG.fromstring(demo_grammar)
    assert list(generate(grammar, n=0)) == []
    recursive = CFG.fromstring("S -> S S | 'a'")
    assert list(generate(recursive, n=0)) == []


def test_bounded_recursive_depth_still_terminates():
    # An explicit, small depth on a recursive grammar terminates as before.
    g = CFG.fromstring("S -> S S | 'a'")
    assert len(list(generate(g, depth=5))) == 26
    assert len(list(generate(g, depth=6))) == 677


def test_generation_refused_when_budget_exceeded():
    # With a tiny budget the explosive grammar is refused quickly and safely
    # (in-process: the low limit trips long before memory is a concern).
    g = CFG.fromstring("S -> S S | 'a'")
    original = generate_mod.MAX_GENERATE_OPERATIONS
    generate_mod.MAX_GENERATE_OPERATIONS = 10_000
    try:
        with pytest.raises(ValueError):
            list(generate(g, depth=8))
    finally:
        generate_mod.MAX_GENERATE_OPERATIONS = original


_TIMEOUT = 30


def _generate_worker(result_q):
    try:
        # The exact reported DoS: default depth, no n, 15-byte recursive grammar.
        g = CFG.fromstring("S -> S S | 'a'")
        try:
            list(generate(g))
            result_q.put(("ok", "enumerated"))
        except ValueError:
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


def test_default_depth_recursive_grammar_is_refused_not_unbounded():
    """generate(recursive_grammar) must be refused, not run unbounded."""
    finished, status, value = _run_in_process(_generate_worker)
    assert finished, "generate() enumerated an unbounded recursive grammar (DoS)"
    assert status == "ok", f"worker raised: {value}"
    assert value == "refused"
