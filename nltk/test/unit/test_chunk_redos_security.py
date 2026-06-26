"""Regression tests for ReDoS in chunk tag-pattern parsing (CWE-1333).

``tag_pattern2re_pattern`` validates a caller-supplied tag pattern against the
module-level ``CHUNK_TAG_PATTERN`` regex. That regex used to contain a nested
quantifier of the ``(A+)*`` form, which exhibits catastrophic (exponential)
backtracking: a short tag pattern ending in a character the pattern cannot
match (e.g. a trailing ``{``) forced the engine into exponential work, hanging
the process. ``CHUNK_TAG_PATTERN`` / ``tag_pattern2re_pattern`` / ``RegexpParser``
are public entry points, so an application that compiles user-supplied chunking
rules could be stalled by a single ~30-character request. The first alternative
is no longer quantified with ``+``, so the match is linear while accepting the
exact same language. See huntr report
https://huntr.com/bounties/aff8ef29-2f20-46a4-ae13-7ce6010e26a5.

The "must not hang" tests run the work in a separate process (spawn) with a
hard timeout and ``terminate()`` on overrun, so a regression to an exponential
regex cannot keep burning CPU for the rest of the suite, and any exception in
the worker is propagated back to the assertions instead of being swallowed.
"""

import multiprocessing
import queue

from nltk.chunk.regexp import CHUNK_TAG_PATTERN, tag_pattern2re_pattern

# A short, unmatchable payload: a run of plain tag characters followed by a
# trailing "{" that ``CHUNK_TAG_PATTERN`` can neither consume nor close. With
# the old ``(A+)*`` regex this took ~minutes; with the de-nested regex it is
# sub-millisecond. 40 chars is already far past the old exponential cliff.
_CRAFTED_PATTERN = "a" * 40 + "{"
# Generous vs. the linear cost (sub-ms after process startup) but far below the
# exponential regression cost, so a regression fails fast and cleanly.
_TIMEOUT = 15


def _match_worker(result_q):
    try:
        result_q.put(("ok", bool(CHUNK_TAG_PATTERN.match(_CRAFTED_PATTERN))))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _convert_worker(result_q):
    try:
        # tag_pattern2re_pattern raises ValueError ("Bad tag pattern") on the
        # unmatchable payload after the (now linear) check. Either outcome means
        # the call terminated rather than hanging.
        try:
            tag_pattern2re_pattern(_CRAFTED_PATTERN)
            result_q.put(("ok", "accepted"))
        except ValueError:
            result_q.put(("ok", "rejected"))
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


def test_chunk_tag_pattern_preserves_accepted_language():
    """The de-nested regex must accept/reject the same patterns as before."""
    # Known-valid tag patterns (after the ``<``/``>`` -> ``(<( )>)`` rewrite that
    # ``tag_pattern2re_pattern`` performs before the check) still match.
    for valid in ("(<(DT)>)", "(<(NN)>)(<(NN)>)", "(<(JJ)>)(<(NN)>)", "(<(V)>)"):
        assert CHUNK_TAG_PATTERN.match(valid), f"valid pattern rejected: {valid!r}"
    # Braces with repetition counts are still accepted.
    assert CHUNK_TAG_PATTERN.match("a{2,}")
    assert CHUNK_TAG_PATTERN.match("a{3,5}")
    # Bare/unbalanced angle brackets and a trailing brace are still rejected.
    assert not CHUNK_TAG_PATTERN.match("a{")
    assert not CHUNK_TAG_PATTERN.match("<")
    assert not CHUNK_TAG_PATTERN.match(">")


def test_tag_pattern2re_pattern_still_converts_real_patterns():
    """End-to-end: ordinary tag patterns still convert without error."""
    # A normal chunking rule body must compile to a regular-expression pattern.
    assert tag_pattern2re_pattern("<DT>?<JJ>*<NN>")
    assert tag_pattern2re_pattern("<NN.*>")


def test_chunk_tag_pattern_is_linear_on_crafted_pattern():
    """A short unmatchable pattern must not blow up (ReDoS)."""
    finished, status, payload = _run_in_process(_match_worker)
    assert finished, "CHUNK_TAG_PATTERN hung on a crafted tag pattern (ReDoS)"
    assert status == "ok", f"worker raised: {payload}"
    # The crafted pattern does not match; the point is that it returns at all.
    assert payload is False


def test_tag_pattern2re_pattern_does_not_hang_on_crafted_pattern():
    """End-to-end: converting a malicious tag pattern must terminate (not hang)."""
    finished, status, payload = _run_in_process(_convert_worker)
    assert finished, "tag_pattern2re_pattern hung on a crafted tag pattern (ReDoS)"
    assert status == "ok", f"convert raised in worker: {payload}"
    assert payload == "rejected"
