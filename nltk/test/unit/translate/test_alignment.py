"""Regression tests for nltk.translate.Alignment.

Covers the unbounded-allocation DoS (CWE-770; CVE-2026-12837): a tiny pair with a
huge left index used to force a dense per-left-index list allocation, because the
index was ``[[] for _ in range(self._len + 1)]``. The index is now sparse (a dict
keyed by the left indices that occur). These tests confirm the index is sparse and
that the public indexing / range behaviour is preserved.

The allocation test runs in a spawned process with a hard timeout so a regression
to the dense allocation cannot OOM or hang the rest of the suite.
"""

import multiprocessing
import queue

import pytest

from nltk.translate.api import Alignment


def test_index_is_sparse_not_dense():
    a = Alignment([(0, 0), (0, 1), (1, 2), (2, 2)])
    a.range()  # builds the index
    assert isinstance(a._index, dict)
    # keyed only by the left indices that occur, not range(_len + 1)
    assert set(a._index) == {0, 1, 2}


def test_getitem_and_range_preserved():
    a = Alignment([(0, 0), (0, 1), (1, 2), (2, 2)])
    assert sorted(a[0]) == [(0, 0), (0, 1)]
    assert sorted(a[2]) == [(2, 2)]
    assert a[5] == []  # a left index with no alignments
    assert a.range() == [0, 1, 2]
    assert a.range([0]) == [0, 1]
    assert a.range([1, 2]) == [2]
    assert sorted(a.invert()[2]) == [(2, 1), (2, 2)]


def test_getitem_rejects_non_integer_keys():
    # The sparse index has no contiguous range to slice; non-integer keys must
    # raise rather than silently return [] (which would mask caller bugs).
    a = Alignment([(0, 0), (0, 1), (1, 2)])
    for bad in (slice(0, 2), "0", 1.0, (0, 1)):
        with pytest.raises(TypeError):
            a[bad]


# A left index large enough to make a dense ``[[] for _ in range(_HUGE + 1)]``
# regression unmistakable (the index would hold _HUGE + 1 keys instead of 2),
# yet small enough that even if such a dense list were built it stays ~128 MB --
# detected by the key-count assertion below without risking an OOM of the host.
_HUGE = 2_000_000
_TIMEOUT = 15


def _alloc_worker(result_q):
    try:
        a = Alignment.fromstring(f"0-0 {_HUGE}-1")
        a.range()  # triggers _build_index
        _ = a[0]
        result_q.put(("ok", len(a._index)))
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


def test_huge_left_index_does_not_allocate():
    """A tiny pair with a huge left index must not allocate a dense index."""
    finished, status, value = _run_in_process(_alloc_worker)
    assert finished, "Alignment allocated a dense index for a huge left index (DoS)"
    assert status == "ok", f"worker raised: {value}"
    assert value == 2, f"index must be sparse (2 keys), got {value}"
