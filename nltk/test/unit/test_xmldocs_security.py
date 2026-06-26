"""Regression tests for catastrophic backtracking in XMLCorpusView (CWE-1333).

``_VALID_XML_RE`` validates each fragment read by ``XMLCorpusView``. Its comment,
CDATA and doctype alternatives used to be able to span their own terminators, so
a fragment ending in an unterminated piece made the ``( ... )* \\Z`` structure
re-partition the input exponentially. Each alternative is now pinned to its first
terminator, making validation linear.

The "must not hang" tests run the work in a separate process (spawn) with a hard
timeout and ``terminate()`` on overrun, so a regression to an exponential regex
cannot keep burning CPU for the rest of the suite.
"""

import multiprocessing
import queue

from nltk.corpus.reader.xmldocs import XMLCorpusView
from nltk.data import FileSystemPathPointer

# A handful of closed pieces followed by an unterminated tail so ``\Z`` fails.
# With the old spanning regex even ~30 of these took minutes (exponential);
# linear now (sub-millisecond after process startup).
_N = 60
_PAYLOADS = {
    "comment": "<!--c-->" * _N + "<!--" + "a" * 10,
    "doctype": "<!DOCTYPE d>" * _N + "<!DOCTYPE " + "a" * 10,
    "cdata": "<![CDATA[x]]>" * _N + "<![CDATA[" + "a" * 10,
}
_TIMEOUT = 15


def _regex_worker(result_q, payload):
    try:
        result_q.put(("ok", XMLCorpusView._VALID_XML_RE.match(payload) is not None))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def _view_worker(result_q, path):
    try:
        view = XMLCorpusView(FileSystemPathPointer(path), ".*")
        # Reading drives _read_xml_fragment / _VALID_XML_RE. A malformed file may
        # raise ValueError; the point is that it must *terminate*, not hang.
        try:
            list(view)
            result_q.put(("ok", "read"))
        except ValueError:
            result_q.put(("ok", "raised"))
    except BaseException as exc:
        result_q.put(("error", repr(exc)))


def _run_in_process(target, args=()):
    """Run ``target(result_q, *args)`` in a spawned process with a timeout."""
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


def test_valid_xml_re_does_not_hang():
    """_VALID_XML_RE must validate crafted fragments in linear time (no ReDoS)."""
    for name, payload in _PAYLOADS.items():
        finished, status, value = _run_in_process(_regex_worker, (payload,))
        assert finished, f"_VALID_XML_RE hung on a crafted {name} fragment (ReDoS)"
        assert status == "ok", f"worker raised on {name}: {value}"


def test_xmlcorpusview_does_not_hang_on_crafted_file(tmp_path):
    """End-to-end: reading a crafted corpus file must terminate, not hang."""
    malicious = tmp_path / "evil.xml"
    malicious.write_text(_PAYLOADS["comment"], encoding="utf-8")

    finished, status, value = _run_in_process(_view_worker, (str(malicious),))
    assert finished, "XMLCorpusView hung on a crafted corpus file (ReDoS)"
    assert status == "ok", f"reader raised unexpectedly: {value}"
