"""Regression tests for ReDoS in ReviewsCorpusReader (CWE-1333).

The ``FEATURES`` regex extracts ``feature[+N]`` annotations from each review
line. With an unbounded feature label, ``re.findall`` rescans a long
bracket-less line quadratically, so a crafted corpus line can hang the reader.
The label length is now bounded, making extraction linear.

The "must not hang" tests run the work in a separate process (spawn) with a
hard timeout and ``terminate()`` on overrun, so a regression to a quadratic
regex cannot keep burning CPU for the rest of the suite, and any exception in
the worker is propagated back to the assertions instead of being swallowed.
"""

import multiprocessing
import queue

from nltk.corpus.reader.reviews import FEATURES, ReviewsCorpusReader

# A long, bracket-less word run: ~250 KB. Linear with the bounded regex
# (milliseconds); ~quadratic and ~50 s with the old unbounded one.
_CRAFTED_LINE = "word " * 50_000
# Generous vs. the linear cost (which is ~ms after process startup), but far
# below the quadratic regression cost, so a regression fails fast and cleanly.
_TIMEOUT = 15


def _features_worker(result_q):
    try:
        result_q.put(("ok", FEATURES.findall(_CRAFTED_LINE)))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _reader_worker(result_q, root, fileid):
    try:
        reviews = ReviewsCorpusReader(root, fileid).reviews()
        # Return only picklable data: number of reviews and the first review's
        # features (a list of (feature, score) string tuples).
        result_q.put(("ok", (len(reviews), reviews[0].features())))
    except BaseException as exc:
        result_q.put(("error", repr(exc)))


def _run_in_process(target, args=()):
    """Run ``target(result_q, *args)`` in a spawned process with a timeout.

    Returns ``(finished, status, payload)``. If the worker overruns ``_TIMEOUT``
    it is terminated (no lingering CPU) and ``finished`` is ``False``.
    """
    ctx = multiprocessing.get_context("spawn")
    result_q = ctx.Queue()
    proc = ctx.Process(target=target, args=(result_q, *args))
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


def test_features_regex_preserves_normal_extraction():
    """The bounded regex must extract the same features as before on real data."""
    line = "battery life[+2] and the zoom[-1] are ok"
    assert FEATURES.findall(line) == [("battery life", "+2"), ("and the zoom", "-1")]
    assert FEATURES.findall("size[+3]") == [("size", "+3")]
    assert FEATURES.findall("no feature annotation here") == []


def test_features_regex_is_linear_on_crafted_line():
    """A long, bracket-less word run must not blow up (ReDoS)."""
    finished, status, payload = _run_in_process(_features_worker)
    assert finished, "FEATURES regex hung on a crafted line (ReDoS)"
    assert status == "ok", f"worker raised: {payload}"
    assert payload == []


def test_reviews_reader_does_not_hang_on_crafted_corpus(tmp_path):
    """End-to-end: reading a malicious review file must terminate and succeed."""
    (tmp_path / "r.txt").write_text("[t]title\n" + _CRAFTED_LINE + "\n")

    finished, status, payload = _run_in_process(
        _reader_worker, (str(tmp_path), "r.txt")
    )
    assert finished, "ReviewsCorpusReader hung on a crafted corpus line (ReDoS)"
    assert status == "ok", f"reader raised in worker: {payload}"
    num_reviews, features = payload
    # The call actually succeeded (output populated), not silently swallowed.
    assert num_reviews == 1
    assert features == []
