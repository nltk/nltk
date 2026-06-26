"""Regression tests for two DoS defects in NLTK LEPOR word alignment
(``nltk.translate.lepor.alignment``, used by ``sentence_lepor``/``corpus_lepor``).

* Uncaught ``IndexError`` on ordinary input (CWE-20): the match-flag list was
  created empty and then assigned into by index, raising
  ``IndexError: list assignment index out of range`` whenever a hypothesis token
  appears two or more times in the reference -- a very common case.
* Quadratic time (CWE-407): the aligner used ``ref_tokens.count``/``index`` once
  per hypothesis token, i.e. O(len(ref) * len(hyp)). The reference positions are
  now indexed once up front, making the aligner linear.

(Removing the crash also exposed a latent copy-paste bug in the "no windowed
match" branch that appended the chosen index twice; that duplicate is removed so
each hypothesis token contributes at most one alignment.)
"""

import multiprocessing
import os
import random
import traceback

from nltk.translate.lepor import alignment


def test_alignment_handles_repeated_tokens():
    """A hypothesis token repeated in the reference must not raise IndexError."""
    assert alignment(["the", "cat", "the"], ["the"]) == [3]
    assert alignment(["a", "b", "a", "b"], ["a", "b"]) == [3, 4]
    assert alignment(["a", "b", "a"], ["a"]) == [3]


def test_alignment_preserved_on_distinct_reference():
    """Behaviour on the previously-working domain (no repeats) is unchanged."""
    assert alignment(["the", "cat", "sat"], ["the", "dog", "sat"]) == [1, 3]
    assert alignment([], ["a"]) == []
    assert alignment(["x"], []) == []
    assert alignment(["a", "b", "c"], ["c", "a"]) == [3, 1]


def test_alignment_at_most_one_alignment_per_hyp_token():
    """Each hypothesis token yields at most one alignment (no double-append)."""
    rng = random.Random(7)
    vocab = ["a", "b", "c"]  # tiny vocab -> lots of repeats -> the else branch
    for _ in range(2000):
        ref = [rng.choice(vocab) for _ in range(rng.randint(0, 8))]
        hyp = [rng.choice(vocab) for _ in range(rng.randint(0, 8))]
        assert len(alignment(ref, hyp)) <= len(hyp)


def _alignment_worker(n):
    """Run the aligner on a large disjoint input; exit 0 on success, 3 on error.

    On error the traceback is printed before exiting so a failure here is
    diagnosable in CI -- the parent process only sees the numeric exit code.
    """
    try:
        ref = [f"r{i}" for i in range(n)]
        hyp = [f"h{i}" for i in range(n)]
        alignment(ref, hyp)
        os._exit(0)
    except BaseException:
        traceback.print_exc()
        os._exit(3)


def test_alignment_is_linear_not_quadratic():
    """A large low-overlap input must finish quickly (linear), not tie up a core.

    Run in a spawned process with a hard deadline: the linear aligner returns in
    milliseconds, while the previous quadratic version needs well over a minute
    at this size, so a regression is terminated and fails the test instead of
    burning CPU for the rest of the suite.
    """
    n = 120_000
    deadline = 30
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_alignment_worker, args=(n,))
    proc.start()
    proc.join(deadline)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "alignment() did not finish in time: quadratic blow-up regressed"
        )
    assert proc.exitcode == 0, f"alignment() worker failed (exit {proc.exitcode})"
