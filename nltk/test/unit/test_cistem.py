"""Regression tests for the quadratic-time DoS in the Cistem stemmer
(CWE-770; CVE-2026-12868).

``Cistem._segment_inner`` stripped 1-2 trailing characters per iteration with a
compiled ``re`` pattern's ``Pattern.subn("", word)``, which rebuilt the whole
remaining string each time -- O(n) work over O(n) iterations, i.e. O(n**2) in the
word length. A single
crafted word of a few tens of KB pinned a CPU core. The loop now strips from a
list in O(1) per step (O(n) overall) while producing byte-identical output.

The "must stay linear" test runs in a spawned process with a hard timeout, and
the worker reports its outcome through its exit code (no queue/thread, so it is
robust on free-threaded builds), so a regression to the O(n**2) loop cannot hang
the suite.
"""

import multiprocessing
import os

from nltk.stem.cistem import Cistem

# (word, expected stem, expected (stem, rest)) for the default (case-sensitive)
# stemmer -- these are the examples documented in Cistem.stem / Cistem.segment.
_CASE_SENSITIVE = [
    ("Speicherbehältern", "speicherbehalt", ("speicherbehält", "ern")),
    ("Grenzpostens", "grenzpost", ("grenzpost", "ens")),
    ("Ausgefeiltere", "ausgefeilt", ("ausgefeilt", "ere")),
]
# expected stems / segments for the case-insensitive stemmer.
_CASE_INSENSITIVE = [
    ("Speicherbehältern", "speicherbehal", ("speicherbehäl", "tern")),
    ("Grenzpostens", "grenzpo", ("grenzpo", "stens")),
    ("Ausgefeiltere", "ausgefeil", ("ausgefeil", "tere")),
]


def test_stem_and_segment_examples_preserved():
    stemmer = Cistem()
    for word, stem, segment in _CASE_SENSITIVE:
        assert stemmer.stem(word) == stem
        assert stemmer.segment(word) == segment
    ci = Cistem(case_insensitive=True)
    for word, stem, segment in _CASE_INSENSITIVE:
        assert ci.stem(word) == stem
        assert ci.segment(word) == segment


def test_empty_and_short_words():
    stemmer = Cistem()
    assert stemmer.stem("") == ""
    assert stemmer.segment("") == ("", "")
    assert stemmer.stem("Die") == "die"  # <= 3 chars: returned unchanged (lowered)


_TIMEOUT = 20
# A word that the pre-fix O(n**2) loop would take ~minutes on (the loop runs
# ~n iterations, each rebuilding the whole ~n-char string), but the O(n) fix
# stems in milliseconds. Made of repeated strippable suffixes to maximise the
# iteration count.
_BIG_WORD = "esn" * 40000  # 120k chars


def _stem_worker():
    try:
        Cistem().stem(_BIG_WORD)
        os._exit(0)  # finished quickly -> linear
    except BaseException:
        os._exit(3)


def test_long_word_stems_in_linear_time():
    """A long word must stem quickly, not run the old O(n**2) loop."""
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_stem_worker)
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "Cistem.stem did not finish in time -> quadratic-time DoS (CWE-770)"
        )
    assert proc.exitcode == 0, f"worker failed (exit code {proc.exitcode})"
