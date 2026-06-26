"""Regression tests for the unbounded-default-``max_len`` DoS in
``nltk.util.everygrams`` (CWE-770; CVE-2026-12861).

With ``max_len`` left at its ``-1`` default it expands to ``len(sequence)``, so
enumerating every n-gram of every length from ``min_len`` to ``len(sequence)``
over each window yields O(n**2) tuples totalling O(n**3) elements -- a
few-thousand-token sequence then allocates gigabytes and OOM-kills the process.
The defaulted ``max_len`` is now capped by ``MAX_EVERYGRAMS_DEFAULT_LEN``; a
longer sequence with the default raises ``ValueError`` asking for an explicit
``max_len``. An explicitly supplied ``max_len`` is never capped.

The "must not allocate" test runs in a spawned process with a hard timeout, and
the worker reports its outcome through its exit code (no queue/thread, so it is
robust on free-threaded builds), so a regression cannot OOM/hang the suite.
"""

import multiprocessing
import os

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


_TIMEOUT = 60
# Worker outcomes, reported via exit code (avoids a result queue / feeder thread,
# which is fragile on free-threaded builds).
_EXIT_REFUSED = 0  # ValueError raised before any allocation (the expected result)
_EXIT_ENUMERATED = 2  # the unbounded enumeration ran to completion (regression)
_EXIT_OTHER = 3  # any other failure


def _everygrams_worker():
    # With the default max_len this would enumerate O(n**2) tuples totalling
    # O(n**3) elements if the guard were removed. Consume the iterator WITHOUT
    # materializing it into a list: each tuple is transient, so peak memory
    # stays low and a regression is caught by the parent's timeout rather than
    # risking an OS OOM kill that could destabilize the whole CI job.
    toks = [str(i) for i in range(2000)]
    try:
        for _ in everygrams(toks):
            pass
        os._exit(_EXIT_ENUMERATED)
    except ValueError:
        os._exit(_EXIT_REFUSED)
    except BaseException:
        os._exit(_EXIT_OTHER)


def test_oversized_default_does_not_allocate():
    """everygrams(long_seq) with the default max_len must be refused, not run."""
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_everygrams_worker)
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "everygrams() did not return quickly -> unbounded O(n**3) allocation (DoS)"
        )
    assert proc.exitcode == _EXIT_REFUSED, (
        "everygrams() with the default max_len over a long sequence was not "
        f"refused before allocating (worker exit code {proc.exitcode}); "
        "expected a fast ValueError"
    )
