"""Regression tests for nltk.metrics.ConfusionMatrix (CWE-770; CVE-2026-12839).

A dense V x V matrix (V = number of distinct labels) was allocated and retained,
so an all-distinct input forced O(V**2) memory and OOM-killed the worker. The
matrix is now a sparse dict keyed by the observed (reference index, test index)
pairs. These tests confirm the storage is sparse and the public API is preserved.

The allocation test runs in a spawned process with a hard timeout so a regression
to the dense allocation cannot OOM or hang the rest of the suite.
"""

import multiprocessing
import queue

from nltk.metrics import ConfusionMatrix

_REF = "DET NN VB DET JJ NN NN IN DET NN".split()
_TEST = "DET VB VB DET NN NN NN IN DET NN".split()


def test_storage_is_sparse():
    cm = ConfusionMatrix(_REF, _TEST)
    assert isinstance(cm._confusion, dict)
    # one entry per observed (ref, test) pair, not len(values) ** 2
    observed = {(r, t) for r, t in zip(_REF, _TEST)}
    assert len(cm._confusion) == len(observed)


def test_public_api_preserved():
    cm = ConfusionMatrix(_REF, _TEST)
    assert cm["NN", "NN"] == 3
    assert cm["DET", "VB"] == 0  # a pair that never occurs
    assert cm.recall("NN") == 0.75
    assert cm.precision("NN") == 0.75
    assert repr(cm) == "<ConfusionMatrix: 8/10 correct>"
    # pretty_format still renders (exact output is covered by metrics.doctest)
    assert "(row = reference; col = test)" in cm.pretty_format()


# A dense matrix at this size costs ~200 MB (V**2 cells); the sparse map costs a
# few MB. The threshold separates the two without attempting a multi-GB
# allocation when regressed.
_N = 5000
_MAX_BYTES = 50_000_000
_TIMEOUT = 15


def _alloc_worker(result_q):
    try:
        import tracemalloc

        ref = [str(i) for i in range(_N)]
        test = [str(_N - 1 - i) for i in range(_N)]
        tracemalloc.start()
        ConfusionMatrix(ref, test)  # retains self._confusion
        _cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result_q.put(("ok", peak))
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


def test_all_distinct_input_does_not_allocate_dense_matrix():
    """An all-distinct sequence must not allocate a dense V x V matrix."""
    finished, status, peak = _run_in_process(_alloc_worker)
    assert finished, "ConfusionMatrix did not finish (dense V x V allocation OOM/hang)"
    assert status == "ok", f"worker raised: {peak}"
    assert (
        peak < _MAX_BYTES
    ), f"allocated {peak/1e6:.0f} MB for {_N} distinct labels (DoS)"
