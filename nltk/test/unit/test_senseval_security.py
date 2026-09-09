"""Regression tests for ReDoS in SensevalCorpusReader (CWE-1333).

``_fixXML`` normalises Senseval pseudo-XML before parsing. Several of its
substitutions (the two ``<p="..."/>`` tag rewrites and the lone-``&`` fix) scan a
run of whitespace / token characters that must be followed by a trailing
literal; when that literal is absent, ``sub`` retries at every start offset and
re-scans the leading run, so a crafted instance body is quadratic and hangs the
reader. The fix is twofold and changes no output: possessive quantifiers stop
catastrophic backtracking *within* an attempt, and a leading ``(?<![ \\t])`` /
``(?<!\\s)`` anchors each attempt to the start of a run so a mid-run offset is
rejected in O(1) instead of re-consuming the run. Byte-for-byte identical to the
originals (verified against the full real Senseval corpus), now linear.

The "must not hang" tests run the work in a separate process (spawn) with a hard
timeout and ``terminate()`` on overrun, so a regression cannot keep burning CPU
for the rest of the suite, and any exception in the worker is propagated back to
the assertions. The linear-vs-quadratic decision is made on the time the worker
spends in the scan itself (measured in-process), so process spawn and
``import nltk`` cost on a slow CI runner is never mistaken for a ReDoS hang.
"""

import queue
import time

from nltk.corpus.reader.senseval import SensevalCorpusReader, _fixXML

from . import _mp_ctx

# A long token with no <p="..."/> tag: ~128 KB. Linear with the possessive
# patterns (sub-millisecond); ~quadratic and tens of seconds with the old ones.
_CRAFTED_TOKEN = "x" * 128_000

# _TIMEOUT is only a hang-backstop: it kills a worker that never returns so a
# quadratic regression cannot burn CPU for the rest of the suite. It is generous
# on purpose so process spawn + ``import nltk`` on a slow/contended CI runner is
# never mistaken for a hang. The actual linear-vs-quadratic decision is
# _LINEAR_CEILING applied to the in-process scan time (both operations here are
# sub-millisecond when linear, versus tens of seconds for the old quadratic
# patterns), which excludes spawn/import cost.
_TIMEOUT = 120
_LINEAR_CEILING = 5.0

# Crafted shapes that stress the _fixXML substitutions in different ways. Each
# lacks (or misplaces) the trailing <p="..."/> tag so the ``sub`` retries at
# every offset; the guard (leading (?<![ \t])/(?<!\s) anchors + possessive
# quantifiers) must keep every one linear rather than re-scanning a long run
# quadratically and burning the redos time budget.
_REDOS_SHAPES = [
    _CRAFTED_TOKEN,  # long token, no tag (length must be unchanged)
    " " * 128_000 + '<p="NN"/>',  # long whitespace run before a real tag
    "\t" * 128_000 + '<p="NN"/>',  # same, with tabs
    "<p=" * 40_000,  # many partial tag openers, none closed
    '<p="' + '"' * 120_000 + '"/>',  # long quote run inside a tag
    'x <p="' + "y" * 120_000,  # unterminated tag value after a real token
]


def _fixxml_worker(result_q):
    try:
        # Run every crafted shape in this one child so the whole ReDoS matrix
        # costs a single process spawn + ``import nltk`` rather than one each.
        # Return only per-shape (result_length, op_elapsed) small tuples; putting
        # the full ~128 KB results on the Queue could exceed the OS pipe buffer
        # and deadlock against the parent's join(). op_elapsed is measured
        # in-process so spawn/import latency is excluded.
        measurements = []
        for shape in _REDOS_SHAPES:
            start = time.perf_counter()
            length = len(_fixXML(shape))
            measurements.append((length, time.perf_counter() - start))
        worst = max(dt for _, dt in measurements)
        result_q.put(("ok", measurements, worst))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc), 0.0))


def _reader_worker(result_q, root, fileid):
    try:
        start = time.perf_counter()
        instances = SensevalCorpusReader(root, fileid).instances()
        result_q.put(("ok", len(instances), time.perf_counter() - start))
    except BaseException as exc:
        result_q.put(("error", repr(exc), 0.0))


def _run_in_process(target, args=()):
    """Run ``target`` in a separate process. Returns
    ``(finished, status, payload, op_elapsed)``; ``op_elapsed`` is the in-process
    scan time (spawn/import excluded), so a slow runner cannot turn a linear scan
    into a false ReDoS failure. ``finished`` is False only on a true hang."""
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


def test_fixxml_preserves_behavior():
    """The possessive patterns plus the leading (?<![ \\t])/(?<!\\s) anchors must
    transform tags and lone ampersands exactly as before. The anchors only skip
    mid-run start offsets that can never match, so output is unchanged; these
    cases exercise the leading-whitespace and lone-amp branches specifically."""
    assert _fixXML('cat <p="NN"/> sat') == ' <wf pos="NN">cat</wf> sat'
    assert _fixXML("word \"  <p='\"'/> rest") == "word <wf pos='\"'>\"</wf> rest"
    assert _fixXML("plain text no tags here") == "plain text no tags here"
    # lone ampersand -> &amp; (the (?<!\\s)(\\s+)&(\\s+) branch)
    assert _fixXML("a & b") == "a &amp; b"
    assert _fixXML("x & y & z") == "x &amp; y &amp; z"
    # multi-space run before a token collapses to one leading space, same as the
    # unanchored pattern (the (?<![ \\t]) branch starts at the first space only)
    assert _fixXML('a  word<p="NN"/>') == 'a <wf pos="NN">word</wf>'
    assert _fixXML('lead <p="VB"/>') == ' <wf pos="VB">lead</wf>'
    assert (
        _fixXML('one <p="A"/> two <p="B"/>')
        == ' <wf pos="A">one</wf> <wf pos="B">two</wf>'
    )


def test_fixxml_is_linear_on_crafted_shapes():
    """Every ReDoS-candidate shape must scan linearly, not hang. All shapes run
    in one child process (a single spawn) and each scan is timed in-process, so
    the pass/fail decision is the scan cost, not interpreter startup on a slow
    runner. A quadratic regression shows up as a per-shape time in seconds
    (or a true hang caught by _TIMEOUT), not milliseconds."""
    finished, status, payload, _worst = _run_in_process(_fixxml_worker)
    assert finished, "_fixXML hung on a crafted shape (ReDoS)"
    assert status == "ok", f"worker raised: {payload}"
    assert len(payload) == len(_REDOS_SHAPES)
    for (length, dt), shape in zip(payload, _REDOS_SHAPES):
        assert isinstance(length, int)  # produced a finite result
        assert dt < _LINEAR_CEILING, (
            f"_fixXML took {dt:.2f}s on shape {shape[:12]!r}...; a linear scan is "
            f"milliseconds, the old quadratic pattern was seconds"
        )
    # The first shape is a long token with no tag: no substitution fires, so its
    # length is unchanged (a sanity check that the fast path is the no-match one).
    assert payload[0][0] == len(_CRAFTED_TOKEN)


def test_senseval_reader_does_not_hang_on_crafted_corpus(tmp_path):
    """End-to-end: reading a malicious instance body must terminate and succeed."""
    (tmp_path / "t.pos").write_text(
        '<lexelt item="t.n">\n<instance id="t.1">\n<context>\n'
        + _CRAFTED_TOKEN
        + "\n</context>\n</instance>\n</lexelt>\n"
    )
    finished, status, payload, op_elapsed = _run_in_process(
        _reader_worker, (str(tmp_path), ["t.pos"])
    )
    assert finished, "SensevalCorpusReader hung on a crafted instance (ReDoS)"
    assert status == "ok", f"reader raised in worker: {payload}"
    assert payload == 1  # one instance parsed
    assert (
        op_elapsed < _LINEAR_CEILING
    ), f"reading a crafted instance took {op_elapsed:.2f}s; should be linear"
