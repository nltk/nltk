"""Regression tests for catastrophic backtracking in XMLCorpusView (CWE-1333).

``_VALID_XML_RE`` validates each fragment read by ``XMLCorpusView``. Its comment,
CDATA and doctype alternatives used to be able to span their own terminators, so
a fragment ending in an unterminated piece made the ``( ... )* \\Z`` structure
re-partition the input exponentially. Each alternative is now pinned to its first
terminator, making validation linear.

The "must not hang" tests run the work in a separate process (spawn) with a hard
timeout and ``terminate()`` on overrun, so a regression to an exponential regex
cannot keep burning CPU for the rest of the suite. Each worker also reports the
time spent in the match/read itself (measured in-process, excluding process spawn
and ``import nltk`` cost); the pass/fail check is that in-process op time, so a
slow or contended runner starting a subprocess is never mistaken for a ReDoS.
``proc.join`` is only a generous hang backstop, not the guard.
"""

import queue
import time

from nltk.corpus.reader.xmldocs import XMLCorpusView
from nltk.data import FileSystemPathPointer

from . import _mp_ctx

# A handful of closed pieces followed by an unterminated tail so ``\Z`` fails.
# With the old spanning regex even ~30 of these took minutes (exponential); about
# 0.1 ms now (linear).
_N = 60
_PAYLOADS = {
    "comment": "<!--c-->" * _N + "<!--" + "a" * 10,
    "doctype": "<!DOCTYPE d>" * _N + "<!DOCTYPE " + "a" * 10,
    "cdata": "<![CDATA[x]]>" * _N + "<![CDATA[" + "a" * 10,
}

# _TIMEOUT is only the hang backstop: a worker that never returns is terminated so
# an exponential regression cannot burn CPU for the rest of the suite. It is
# generous on purpose so process spawn + ``import nltk`` on a slow/contended runner
# is never mistaken for a hang. The ReDoS decision is the in-process op-time
# ceiling below (spawn/import excluded) plus redos's own match timeout, which a
# regression trips and which surfaces here as a worker ``error``.
_TIMEOUT = 120

# The fixed match is ~0.1 ms; the pre-fix exponential form does not finish (redos
# raises). Asserting the in-process match time keeps the ReDoS check load
# invariant; 2 s clears any runner load without masking a blow-up.
_MATCH_CEILING = 2.0


def _regex_worker(result_q, payload):
    try:
        start = time.perf_counter()
        matched = XMLCorpusView._VALID_XML_RE.match(payload) is not None
        result_q.put(("ok", matched, time.perf_counter() - start))
    except BaseException as exc:  # a redos TimeoutError (regression) lands here too
        result_q.put(("error", repr(exc), 0.0))


def _view_worker(result_q, path):
    try:
        view = XMLCorpusView(FileSystemPathPointer(path), ".*")
        # Reading drives _read_xml_fragment / _VALID_XML_RE. A malformed file may
        # raise ValueError; the point is that it must *terminate*, not hang.
        start = time.perf_counter()
        try:
            list(view)
            outcome = "read"
        except ValueError:
            outcome = "raised"
        result_q.put(("ok", outcome, time.perf_counter() - start))
    except BaseException as exc:
        result_q.put(("error", repr(exc), 0.0))


def _run_in_process(target, args=()):
    """Run ``target(result_q, *args)`` in a separate process.

    Returns ``(finished, status, payload, op_elapsed)``. ``op_elapsed`` is the
    time the worker spent in the match/read itself, measured in-process, so
    process spawn and ``import nltk`` cost is excluded and a slow runner cannot
    turn a linear match into a false ReDoS failure. A worker that overruns
    ``_TIMEOUT`` is terminated (no lingering CPU) and ``finished`` is ``False``.
    """
    ctx = _mp_ctx()
    result_q = ctx.Queue()
    proc = ctx.Process(target=target, args=(result_q, *args))
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return False, None, None, None
    try:
        status, payload, op_elapsed = result_q.get_nowait()
    except queue.Empty:
        return True, "error", "worker produced no result", None
    return True, status, payload, op_elapsed


def test_valid_xml_re_does_not_hang():
    """_VALID_XML_RE must validate crafted fragments in linear time (no ReDoS)."""
    for name, payload in _PAYLOADS.items():
        finished, status, value, op_elapsed = _run_in_process(_regex_worker, (payload,))
        assert finished, f"_VALID_XML_RE hung on a crafted {name} fragment (ReDoS)"
        assert status == "ok", f"worker raised on {name}: {value}"
        assert op_elapsed < _MATCH_CEILING, (
            f"_VALID_XML_RE took {op_elapsed:.2f}s on a crafted {name} fragment; a "
            f"linear match is sub-millisecond, the exponential form does not finish"
        )


def test_xmlcorpusview_does_not_hang_on_crafted_file(tmp_path):
    """End-to-end: reading a crafted corpus file must terminate, not hang."""
    malicious = tmp_path / "evil.xml"
    malicious.write_text(_PAYLOADS["comment"], encoding="utf-8")

    finished, status, value, op_elapsed = _run_in_process(
        _view_worker, (str(malicious),)
    )
    assert finished, "XMLCorpusView hung on a crafted corpus file (ReDoS)"
    assert status == "ok", f"reader raised unexpectedly: {value}"
    assert op_elapsed < _MATCH_CEILING, (
        f"XMLCorpusView read took {op_elapsed:.2f}s on a crafted file; a linear "
        f"read is milliseconds, an exponential match does not finish"
    )


# The pre-fix comment alternative that could span its own close marker inside the
# ``( ... )* \Z`` structure: exponential on the crafted comment fragment. The teeth
# test recompiles it so the guard is proven to catch a real regression.
_PRE_FIX_SPANNING_COMMENT_RE = r"[^<]*((<!--.*?-->)[^<]*)*\Z"


def _pre_fix_worker(result_q):
    import re

    from nltk import redos

    try:
        old = redos.compile(_PRE_FIX_SPANNING_COMMENT_RE, flags=re.DOTALL | re.VERBOSE)
        start = time.perf_counter()
        old.match(_PAYLOADS["comment"])
        result_q.put(("ok", None, time.perf_counter() - start))
    except BaseException as exc:
        result_q.put(("error", repr(exc), 0.0))


def test_pre_fix_spanning_comment_trips_the_guard():
    """Teeth: the pre-fix comment alternative is exponential on the crafted
    fragment, so the guard must catch it (redos's match timeout raises, surfacing
    as a worker error, or the op time exceeds the ceiling). Run in the worker so a
    broken timeout cannot hang the suite."""
    finished, status, value, op_elapsed = _run_in_process(_pre_fix_worker)
    assert finished, "the pre-fix pattern hung (redos timeout did not fire)"
    caught = status == "error" or (
        op_elapsed is not None and op_elapsed >= _MATCH_CEILING
    )
    assert (
        caught
    ), f"guard missed the exponential pre-fix pattern: {status} {op_elapsed}"
