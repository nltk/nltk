"""Regression tests for the unbounded-default-``max_len`` DoS in
``nltk.util.everygrams`` (CWE-770; CVE-2026-12861).

With ``max_len`` left at its ``-1`` default it expands to ``len(sequence)``, so
enumerating every n-gram of every length from ``min_len`` to ``len(sequence)``
over each window yields O(n**2) tuples totalling O(n**3) elements -- a
few-thousand-token sequence then allocates gigabytes and OOM-kills the process.
The defaulted ``max_len`` is now capped by ``MAX_EVERYGRAMS_DEFAULT_LEN``; a
longer sequence with the default raises ``ValueError`` asking for an explicit
``max_len``. An explicitly supplied ``max_len`` is never capped.

The "must not allocate" test runs in a spawned process (with an address-space
limit where supported, and a hard timeout) so a regression cannot OOM/hang the
suite.
"""

import multiprocessing
import queue

import pytest

from nltk.util import MAX_EVERYGRAMS_DEFAULT_LEN, everygrams


def test_max_everygrams_default_len_is_a_finite_positive_int():
    assert isinstance(MAX_EVERYGRAMS_DEFAULT_LEN, int)
    assert MAX_EVERYGRAMS_DEFAULT_LEN > 0


def test_behaviour_preserved_for_small_sequences():
    sent = "a b c".split()
    # The values asserted in the everygrams doctest must be unchanged.
    assert list(everygrams(sent)) == [
        ("a",),
        ("a", "b"),
        ("a", "b", "c"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    assert list(everygrams(sent, max_len=2)) == [
        ("a",),
        ("a", "b"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    assert list(everygrams(sent, min_len=2)) == [
        ("a", "b"),
        ("a", "b", "c"),
        ("b", "c"),
    ]


def test_default_allowed_up_to_the_cap():
    # A sequence exactly at the cap still uses the full default (no raise).
    toks = [str(i) for i in range(MAX_EVERYGRAMS_DEFAULT_LEN)]
    out = list(everygrams(toks))
    n = MAX_EVERYGRAMS_DEFAULT_LEN
    assert len(out) == n * (n + 1) // 2


def test_oversized_default_raises():
    # One past the cap with the default max_len is refused -- before allocating.
    toks = [str(i) for i in range(MAX_EVERYGRAMS_DEFAULT_LEN + 1)]
    with pytest.raises(ValueError):
        list(everygrams(toks))


def test_explicit_max_len_is_never_capped():
    # An explicit (bounded) max_len over a long sequence stays linear and allowed.
    toks = [str(i) for i in range(5000)]
    out = list(everygrams(toks, max_len=3))
    # 1-, 2- and 3-grams over 5000 tokens: ~3 * 5000, far below any cube.
    assert len(out) == 5000 + 4999 + 4998


_TIMEOUT = 30
_MEM_LIMIT_BYTES = 1_500_000_000  # 1.5 GB child address-space cap (where supported)


def _everygrams_worker(result_q):
    try:
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (_MEM_LIMIT_BYTES, _MEM_LIMIT_BYTES))
        except Exception:
            pass  # best-effort; the timeout still bounds a regression
        toks = [str(i) for i in range(2000)]  # default max_len -> ~10 GB if unbounded
        try:
            list(everygrams(toks))
            result_q.put(("ok", "materialized"))
        except ValueError:
            result_q.put(("ok", "refused"))
        except MemoryError:
            result_q.put(("ok", "oom"))
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


def test_oversized_default_does_not_allocate():
    """everygrams(long_seq) with the default max_len must be refused, not run."""
    finished, status, value = _run_in_process(_everygrams_worker)
    assert finished, "everygrams() materialized an unbounded O(n**3) result (DoS)"
    assert status == "ok", f"worker raised: {value}"
    assert value == "refused"
