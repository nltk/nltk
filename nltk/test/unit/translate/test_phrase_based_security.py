"""Regression tests for the cubic-blowup DoS in
``nltk.translate.phrase_based.phrase_extraction`` (CWE-770; CVE-2026-12870).

With ``max_phrase_length`` left at its default (0) it expands to the full
sentence length, so the function enumerates O(n**2) phrase pairs, each holding
an O(n)-word string -- O(n**3) total work/memory. A few-hundred-word sentence
pair then pins the CPU and exhausts memory. The defaulted length is now capped
by ``MAX_PHRASE_EXTRACTION_DEFAULT_LEN``; a longer sentence with the default
raises ``ValueError`` asking for an explicit ``max_phrase_length``. An
explicitly supplied ``max_phrase_length`` is never capped.

The "must not run" test runs in a spawned process with a hard timeout, and the
worker reports its outcome through its exit code (no queue/thread, so it is
robust on free-threaded builds), so a regression cannot hang the suite.
"""

import multiprocessing
import os

import pytest

from nltk.translate.phrase_based import (
    MAX_PHRASE_EXTRACTION_DEFAULT_LEN,
    phrase_extraction,
)

# The worked example from the phrase_extraction docstring.
_SRC = "michael assumes that he will stay in the house"
_TRG = "michael geht davon aus , dass er im haus bleibt"
_ALIGN = [
    (0, 0),
    (1, 1),
    (1, 2),
    (1, 3),
    (2, 5),
    (3, 6),
    (4, 9),
    (5, 9),
    (6, 7),
    (7, 7),
    (8, 8),
]


def _diag(n):
    """An n-word source/target pair with a diagonal alignment."""
    src = " ".join("s%d" % i for i in range(n))
    trg = " ".join("t%d" % i for i in range(n))
    return src, trg, [(i, i) for i in range(n)]


def test_max_phrase_extraction_default_len_is_a_finite_positive_int():
    assert isinstance(MAX_PHRASE_EXTRACTION_DEFAULT_LEN, int)
    assert MAX_PHRASE_EXTRACTION_DEFAULT_LEN > 0


def test_docstring_example_preserved():
    # The default expands to max(9, 10) = 10 (<= cap), so the documented
    # 24-phrase result is unchanged.
    assert len(phrase_extraction(_SRC, _TRG, _ALIGN)) == 24


def test_default_allowed_up_to_the_cap():
    # A sentence pair exactly at the cap uses the full default without raising.
    # Use an empty alignment so the default-length guard is exercised at the
    # boundary without building the (near-cubic) phrase set -- the guard depends
    # only on the sentence length, not the alignment, so this still covers the
    # boundary while keeping the test cheap and CI-stable.
    src, trg, _ = _diag(MAX_PHRASE_EXTRACTION_DEFAULT_LEN)
    assert phrase_extraction(src, trg, []) == set()


def test_oversized_default_raises():
    # One past the cap with the default max_phrase_length is refused.
    src, trg, align = _diag(MAX_PHRASE_EXTRACTION_DEFAULT_LEN + 1)
    with pytest.raises(ValueError):
        phrase_extraction(src, trg, align)


def test_explicit_max_phrase_length_is_never_capped():
    # An explicit (bounded) max_phrase_length over a long sentence stays cheap
    # and is allowed regardless of the cap.
    src, trg, align = _diag(2 * MAX_PHRASE_EXTRACTION_DEFAULT_LEN)
    phrases = phrase_extraction(src, trg, align, max_phrase_length=5)
    assert len(phrases) > 0


_TIMEOUT = 60
# Worker outcomes, reported via exit code (avoids a result queue / feeder thread,
# which is fragile on free-threaded builds).
_EXIT_REFUSED = 0  # ValueError raised before running (the expected result)
_EXIT_RAN = 2  # the cubic enumeration ran to completion (regression)
_EXIT_OTHER = 3  # any other failure


def _phrase_worker():
    # A moderate sentence pair, just over the cap. If the guard were removed
    # this runs the cubic path, but at this size it stays well under ~150 MB and
    # ~2 s, so a regression is caught by the non-zero exit code (or the parent's
    # timeout) without risking an OS OOM kill of the whole CI job.
    src, trg, align = _diag(400)
    try:
        phrase_extraction(src, trg, align)
        os._exit(_EXIT_RAN)
    except ValueError:
        os._exit(_EXIT_REFUSED)
    except BaseException:
        os._exit(_EXIT_OTHER)


def test_oversized_default_is_refused_not_run():
    """phrase_extraction(long_pair) with the default must be refused, not run."""
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_phrase_worker)
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "phrase_extraction() did not return quickly -> ran the cubic path (DoS)"
        )
    assert proc.exitcode == _EXIT_REFUSED, (
        "phrase_extraction() with the default max_phrase_length over a long "
        f"sentence pair was not refused (worker exit code {proc.exitcode}); "
        "expected a fast ValueError"
    )
