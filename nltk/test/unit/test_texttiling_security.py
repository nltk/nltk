"""Regression tests for ReDoS in TextTilingTokenizer (CWE-1333).

``_mark_paragraph_breaks`` scans the input for blank-line paragraph breaks with
``[ \\t\\r\\f\\v]*\\n[ \\t\\r\\f\\v]*\\n[ \\t\\r\\f\\v]*``. With the plain greedy
``re`` pattern, ``finditer`` rescans a long horizontal-whitespace run that has no
blank line quadratically, so a crafted whitespace blob hangs ``tokenize()``. The
pattern now uses possessive quantifiers (regex module), making the scan linear.
The whitespace class does not overlap ``"\\n"``, so the matches are unchanged.

The "must not hang" tests run the work in a separate process (spawn) with a hard
timeout and ``terminate()`` on overrun, so a regression to a quadratic regex
cannot keep burning CPU for the rest of the suite, and any exception in the
worker is propagated back to the assertions instead of being swallowed.
"""

import multiprocessing
import queue

from nltk.tokenize.texttiling import TextTilingTokenizer

# A long horizontal-whitespace run with no blank line: ~256 KB. Linear with the
# possessive pattern (sub-millisecond); ~quadratic and tens of seconds with the
# old greedy one.
_CRAFTED_TEXT = " \t" * 128_000
_TIMEOUT = 15

# stopwords are passed explicitly so constructing the tokenizer needs no corpus
# download; the vulnerable scan is in _mark_paragraph_breaks, before any
# stopword use.
_STOPWORDS = ["the", "a", "of", "and", "to"]


def _tokenizer():
    return TextTilingTokenizer(stopwords=_STOPWORDS)


def _mark_worker(result_q):
    try:
        result_q.put(("ok", _tokenizer()._mark_paragraph_breaks(_CRAFTED_TEXT)))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _tokenize_worker(result_q):
    try:
        # A whitespace blob has no paragraph breaks, so tokenize() legitimately
        # raises ValueError after the (now linear) scan. Either outcome means the
        # call terminated rather than hanging.
        try:
            _tokenizer().tokenize(_CRAFTED_TEXT)
        except ValueError:
            pass
        result_q.put(("ok", "terminated"))
    except BaseException as exc:
        result_q.put(("error", repr(exc)))


def _run_in_process(target):
    """Run ``target(result_q)`` in a spawned process with a timeout.

    Returns ``(finished, status, payload)``. If the worker overruns ``_TIMEOUT``
    it is terminated (no lingering CPU) and ``finished`` is ``False``.
    """
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


def test_mark_paragraph_breaks_preserves_behavior():
    """The possessive pattern must find the same paragraph breaks as before."""
    tt = _tokenizer()
    # a blank line between two paragraphs >= MIN_PARAGRAPH (100) apart is a break
    assert tt._mark_paragraph_breaks("x" * 120 + "\n\n" + "y" * 120) == [0, 120]
    # horizontal whitespace inside the break does not change the break position
    # (the match still starts where the trailing whitespace of para one begins)
    assert tt._mark_paragraph_breaks("x" * 120 + "  \n  \n  " + "y" * 120) == [0, 120]
    # no blank line -> only the implicit break at position 0
    assert tt._mark_paragraph_breaks("a single line with no breaks") == [0]
    # breaks closer than MIN_PARAGRAPH (100) are not recorded
    assert tt._mark_paragraph_breaks("x" * 50 + "\n\n" + "y" * 50) == [0]


def test_mark_paragraph_breaks_is_linear_on_whitespace_blob():
    """A long whitespace run with no blank line must not blow up (ReDoS)."""
    finished, status, payload = _run_in_process(_mark_worker)
    assert finished, "_mark_paragraph_breaks hung on a whitespace blob (ReDoS)"
    assert status == "ok", f"worker raised: {payload}"
    assert payload == [0]


def test_tokenize_does_not_hang_on_whitespace_blob():
    """End-to-end: tokenizing a whitespace blob must terminate (not hang)."""
    finished, status, payload = _run_in_process(_tokenize_worker)
    assert finished, "TextTilingTokenizer.tokenize hung on a whitespace blob (ReDoS)"
    assert status == "ok", f"tokenize raised in worker: {payload}"
