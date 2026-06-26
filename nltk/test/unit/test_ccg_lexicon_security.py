"""Regression test for ReDoS in CCG lexicon parsing (CWE-1333).

``LEX_RE`` parses each lexicon line. Its identifier group ``[\\S_]+`` and the
arrow alternative ``[-=]+>`` both match ``-``/``=``, so a line with a long
``-``/``=`` run and no closing ``>`` made the engine slide the boundary across the
run and re-scan for the absent arrow, quadratically. Requiring whitespace before
the separator fixes the boundary, making parsing linear.

The "must not hang" tests run the work in a separate process (spawn) with a hard
timeout and ``terminate()`` on overrun, so a regression to the quadratic regex
cannot keep burning CPU for the rest of the suite.
"""

import multiprocessing
import queue

from nltk.ccg.lexicon import LEX_RE, fromstring

# One lexicon line: an identifier then a long run of '=' with no closing '>', so
# the arrow can never complete. ~tens of seconds with the old quadratic regex;
# sub-millisecond now (after process startup).
_CRAFTED = "a" + "=" * 200_000
_TIMEOUT = 15


def _regex_worker(result_q):
    try:
        result_q.put(("ok", LEX_RE.match(_CRAFTED) is not None))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _fromstring_worker(result_q):
    try:
        # A line with no valid entry makes fromstring raise (AttributeError on
        # the None match); the point is that it must *terminate*, not hang.
        fromstring(_CRAFTED)
        result_q.put(("ok", "parsed"))
    except Exception:
        result_q.put(("ok", "raised"))
    except BaseException as exc:
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


def test_lex_re_does_not_hang():
    """LEX_RE must process a crafted lexicon line in linear time (no ReDoS)."""
    finished, status, value = _run_in_process(_regex_worker)
    assert finished, "LEX_RE hung on a crafted lexicon line (ReDoS)"
    assert status == "ok", f"worker raised: {value}"


def test_fromstring_does_not_hang():
    """End-to-end: fromstring() must terminate on a crafted lexicon line."""
    finished, status, value = _run_in_process(_fromstring_worker)
    assert finished, "fromstring() hung on a crafted lexicon line (ReDoS)"
    assert status == "ok", f"worker raised unexpectedly: {value}"


def test_lex_re_parses_spaced_and_compact_entries():
    """The ReDoS fix keeps both the whitespace-separated and the compact
    ``ident<sep>rhs`` forms working, and the identifier no longer absorbs part of
    the arrow (e.g. ``a-->b`` splits as ``a``/``-->``/``b``, not ``a-``/``->``)."""
    assert LEX_RE.match("the => Det").groups() == ("the", "=>", "Det")
    assert LEX_RE.match("Det :: NP/N").groups() == ("Det", "::", "NP/N")
    assert LEX_RE.match("a-->b").groups() == ("a", "-->", "b")
    assert LEX_RE.match("Det::NP/N").groups() == ("Det", "::", "NP/N")
