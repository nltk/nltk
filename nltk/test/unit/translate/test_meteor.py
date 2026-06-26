import multiprocessing
import queue
import unittest

from nltk.translate.meteor_score import meteor_score, single_meteor_score


class TestMETEOR(unittest.TestCase):
    reference = [["this", "is", "a", "test"], ["this", "is" "test"]]
    candidate = ["THIS", "Is", "a", "tEST"]

    def test_meteor(self):
        score = meteor_score(self.reference, self.candidate, preprocess=str.lower)
        assert score == 0.9921875

    def test_reference_type_check(self):
        str_reference = [" ".join(ref) for ref in self.reference]
        self.assertRaises(TypeError, meteor_score, str_reference, self.candidate)

    def test_candidate_type_check(self):
        str_candidate = " ".join(self.candidate)
        self.assertRaises(TypeError, meteor_score, self.reference, str_candidate)


# ---------------------------------------------------------------------------
# Matching must be linear, not quadratic, on low-overlap text (CWE-770; CVE-2026-12929)
# ---------------------------------------------------------------------------


def test_single_meteor_score_values_preserved():
    # The documented scores are unchanged by the linear-time matcher.
    reference = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "that",
        "ensures",
        "that",
        "the",
        "military",
        "will",
        "forever",
        "heed",
        "Party",
        "commands",
    ]
    hypothesis = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "which",
        "ensures",
        "that",
        "the",
        "military",
        "always",
        "obeys",
        "the",
        "commands",
        "of",
        "the",
        "party",
    ]
    assert round(single_meteor_score(reference, hypothesis), 4) == 0.6944
    # No overlap -> 0.0.
    assert single_meteor_score(["this", "is", "a", "cat"], ["x", "y", "z"]) == 0.0


_TIMEOUT = 30
# Two disjoint token sequences: every hypothesis token misses every reference
# token, so the pre-fix nested scan ran in full O(len_hyp * len_ref) across all
# three matching stages (~tens of seconds at this size); the fix is linear
# (sub-second). CPU-only (a few hundred KB of tokens), so there is no OOM risk.
_N = 32000


def _meteor_worker(result_q):
    try:
        ref = ["r%d" % i for i in range(_N)]
        hyp = ["h%d" % i for i in range(_N)]
        single_meteor_score(ref, hyp)
        result_q.put(("ok", None))
    except BaseException as exc:  # surface to the parent process
        result_q.put(("error", repr(exc)))


def test_meteor_on_disjoint_text_is_linear_time():
    """A low-overlap pair must score in (near-)linear time, not quadratic.

    Runs in a spawned process with a hard timeout and reports status back via a
    queue, so a regression to the quadratic version is terminated (no lingering
    CPU) and any worker exception is surfaced to the assertion.
    """
    ctx = multiprocessing.get_context("spawn")
    result_q = ctx.Queue()
    proc = ctx.Process(target=_meteor_worker, args=(result_q,))
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "METEOR scoring did not finish in time -> quadratic-time DoS (CWE-770)"
        )
    try:
        status, detail = result_q.get_nowait()
    except queue.Empty:
        raise AssertionError("METEOR worker produced no result")
    assert status == "ok", f"worker raised: {detail}"
