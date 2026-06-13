"""Regression tests for ReDoS in SensevalCorpusReader (CWE-1333).

``_fixXML`` normalises Senseval pseudo-XML before parsing. Two of its
substitutions used plain ``re`` patterns whose lazy/greedy whitespace and token
runs rescan a long token / whitespace run that lacks the trailing
``<p="..."/>`` tag quadratically, so a crafted instance body hangs the reader.
The patterns now use possessive quantifiers (regex module), making the scan
linear. The token class ``[^<>\\s]`` cannot cross its separators and ``\\s``
cannot cross the literal ``"``, so the substitutions are unchanged.

The "must not hang" tests run the work in a separate process (spawn) with a hard
timeout and ``terminate()`` on overrun, so a regression cannot keep burning CPU
for the rest of the suite, and any exception in the worker is propagated back to
the assertions instead of being swallowed.
"""

import multiprocessing
import queue

from nltk.corpus.reader.senseval import SensevalCorpusReader, _fixXML

# A long token with no <p="..."/> tag: ~128 KB. Linear with the possessive
# patterns (sub-millisecond); ~quadratic and tens of seconds with the old ones.
_CRAFTED_TOKEN = "x" * 128_000
_TIMEOUT = 15


def _fixxml_worker(result_q):
    try:
        # Return only the length (a small object); putting the full ~128 KB
        # result on the Queue could exceed the OS pipe buffer and deadlock
        # against the parent's join().
        result_q.put(("ok", len(_fixXML(_CRAFTED_TOKEN))))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _reader_worker(result_q, root, fileid):
    try:
        instances = SensevalCorpusReader(root, fileid).instances()
        result_q.put(("ok", len(instances)))
    except BaseException as exc:
        result_q.put(("error", repr(exc)))


def _run_in_process(target, args=()):
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


def test_fixxml_preserves_behavior():
    """The possessive patterns must transform tags exactly as before."""
    assert _fixXML('cat <p="NN"/> sat') == ' <wf pos="NN">cat</wf> sat'
    assert _fixXML("word \"  <p='\"'/> rest") == "word <wf pos='\"'>\"</wf> rest"
    assert _fixXML("plain text no tags here") == "plain text no tags here"


def test_fixxml_is_linear_on_long_token():
    """A long token with no <p="..."/> tag must not blow up (ReDoS)."""
    finished, status, payload = _run_in_process(_fixxml_worker)
    assert finished, "_fixXML hung on a long token (ReDoS)"
    assert status == "ok", f"worker raised: {payload}"
    assert payload == len(_CRAFTED_TOKEN)  # no tag -> length unchanged


def test_senseval_reader_does_not_hang_on_crafted_corpus(tmp_path):
    """End-to-end: reading a malicious instance body must terminate and succeed."""
    (tmp_path / "t.pos").write_text(
        '<lexelt item="t.n">\n<instance id="t.1">\n<context>\n'
        + _CRAFTED_TOKEN
        + "\n</context>\n</instance>\n</lexelt>\n"
    )
    finished, status, payload = _run_in_process(
        _reader_worker, (str(tmp_path), ["t.pos"])
    )
    assert finished, "SensevalCorpusReader hung on a crafted instance (ReDoS)"
    assert status == "ok", f"reader raised in worker: {payload}"
    assert payload == 1  # one instance parsed
