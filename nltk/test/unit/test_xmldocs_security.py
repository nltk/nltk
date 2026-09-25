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
# Old spanning regex: ~30 of these took minutes (exponential); ~0.1 ms now (linear).
_N = 60
_PAYLOADS = {
    "comment": "<!--c-->" * _N + "<!--" + "a" * 10,
    "doctype": "<!DOCTYPE d>" * _N + "<!DOCTYPE " + "a" * 10,
    "cdata": "<![CDATA[x]]>" * _N + "<![CDATA[" + "a" * 10,
}

# Hang backstop: terminates a worker that never returns (a broken redos timeout)
# so it cannot burn CPU; develop's original 15 s bound, kept unrelaxed.
_TIMEOUT = 15

# op_elapsed is wall-clock in the worker; under xdist a descheduled child can fold
# scheduler pause into it, so 2 s (not a tighter bound) removes flake risk. The
# ReDoS guard proper is status == ok (redos raises), so this ceiling costs nothing.
_MATCH_CEILING = 2.0


def _regex_worker(result_q, payload):
    try:
        start = time.perf_counter()
        matched = XMLCorpusView._VALID_XML_RE.match(payload) is not None
        result_q.put(("ok", matched, time.perf_counter() - start))
    except BaseException as exc:
        # A redos TimeoutError (regression) lands here too; op_elapsed is None (not
        # measured), never 0.0, so it cannot be misread as an instant match.
        result_q.put(("error", repr(exc), None))


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
        result_q.put(("error", repr(exc), None))


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


def test_valid_xml_re_matches_well_formed_fragments():
    """The terminator-pinned alternatives must still accept valid XML: pinning the
    comment / CDATA / doctype ends must not start refusing well-formed fragments."""
    for frag in ("<!--hi-->", "<![CDATA[x]]>", "<!DOCTYPE html>", "<a>x</a>"):
        assert XMLCorpusView._VALID_XML_RE.match(
            frag
        ), f"valid fragment refused: {frag!r}"


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

# The teeth probe's redos timeout, a tenth of DEFAULT_TIMEOUT: the guard must stop
# the exponential pattern within 0.5 s of CPU (a starved runner stretches CPU time
# in wall time; the default firing is pinned in test_redos_chokepoint_safety).
_TEETH_TIMEOUT = 0.5


def _pre_fix_worker(result_q):
    import re

    from nltk import redos

    try:
        old = redos.compile(
            _PRE_FIX_SPANNING_COMMENT_RE,
            flags=re.DOTALL | re.VERBOSE,
            timeout=_TEETH_TIMEOUT,
        )
        start = time.perf_counter()
        old.match(_PAYLOADS["comment"])
        result_q.put(("ok", None, time.perf_counter() - start))
    except BaseException as exc:
        result_q.put(("error", repr(exc), None))


def test_pre_fix_spanning_comment_trips_the_guard():
    """Teeth: the pre-fix comment alternative is exponential on the crafted
    fragment, so the guard must catch it (redos's match timeout raises, surfacing
    as a worker error, or the op time exceeds the ceiling). Run in the worker so a
    broken timeout cannot hang the suite."""
    finished, status, value, op_elapsed = _run_in_process(_pre_fix_worker)
    assert finished, "the pre-fix pattern hung (redos timeout did not fire)"
    # only the guard's own TimeoutError counts: any other worker error (an import
    # failure, a typo) would otherwise pass as "caught"
    caught = (status == "error" and "TimeoutError" in value) or (
        op_elapsed is not None and op_elapsed >= _MATCH_CEILING
    )
    assert (
        caught
    ), f"guard missed the exponential pre-fix pattern: {status} {op_elapsed}"


# The pre-fix regex (#3646) in full: every alternative, not only the comment one.
_PRE_FIX_VALID_XML_RE = r"""
        [^<]*
        (
          ((<!--.*?-->)                         |  # comment
           (<![CDATA[.*?]])                     |  # raw character data
           (<!DOCTYPE\s+[^\[]*(\[[^\]]*])?\s*>) |  # doctype decl
           (<[^!>][^>]*>))                         # tag or PI
          [^<]*)*
        \Z"""

_FUZZ_UNITS = [
    "<!DOCTYPE d>",
    "<!DOCTYPE d >",
    "<!DOCTYPE d[x]>",
    "<!DOCTYPE >",
    "<!DOCTYPE d><a>",
    "<![CDATA[x]]>",
    "<!C>",
    "<![x]]>",
    "<!Cx>",
    "<![CDATA[x]]><a>",
    "<!D>",
    "<a>",
    "<a b='c'>",
    "<?pi?>",
]
_FUZZ_TAILS = ["", "<", "<!", "<!DOCTYPE ", "<!DOCTYPE a", "<![CDATA[", "<![CDATA[a"]
_FUZZ_TAILS += ["<!-", "x<", "<a", "<!D", "<!C"]


def test_doctype_cdata_and_tag_families_stay_linear():
    """Every doctype / CDATA / tag unit repeated 40 times before each unterminated
    tail (168 inputs). None was exponential even under the pre-fix regex, and the
    current one must keep each inside the CPU ceiling: it runs under redos's own
    timeout in-process, so an exponential regression raises instead of hanging."""
    import itertools

    slow = []
    for unit, tail in itertools.product(_FUZZ_UNITS, _FUZZ_TAILS):
        text = unit * 40 + tail + "a" * 5
        start = time.process_time()
        XMLCorpusView._VALID_XML_RE.match(text)
        if time.process_time() - start >= _MATCH_CEILING:
            slow.append((unit, tail))
    assert not slow, f"_VALID_XML_RE is super-linear on: {slow[:5]}"


def _pre_fix_full_worker(result_q, name):
    import re

    from nltk import redos

    try:
        old = redos.compile(
            _PRE_FIX_VALID_XML_RE, flags=re.DOTALL | re.VERBOSE, timeout=_TEETH_TIMEOUT
        )
        start = time.perf_counter()
        old.match(_PAYLOADS[name])
        result_q.put(("ok", None, time.perf_counter() - start))
    except BaseException as exc:
        result_q.put(("error", repr(exc), None))


def test_full_pre_fix_regex_trips_the_guard_on_the_comment_payload():
    """Teeth on the whole pre-fix regex, not just its comment alternative: the
    comment payload must still be caught by the guard's TimeoutError."""
    finished, status, value, op_elapsed = _run_in_process(
        _pre_fix_full_worker, ("comment",)
    )
    assert finished, "the full pre-fix regex hung (redos timeout did not fire)"
    assert status == "error" and "TimeoutError" in value, (status, value, op_elapsed)
