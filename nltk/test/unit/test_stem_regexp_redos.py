# Natural Language Toolkit: ReDoS guard for RegexpStemmer
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``RegexpStemmer`` compiles a CALLER's regex and applies it to CALLER text.

A catastrophically backtracking pattern such as ``(a+)+$`` against a short bait
string hangs the interpreter (CWE-1333, ReDoS). The stemmer now routes its
pattern through :func:`nltk.redos.compile`, which puts a wall-clock bound on
matching, mirroring the guard ``nltk.util.re_show`` received in PR #3796.

The hang assertion runs the stemming in a SUBPROCESS with a wall-clock timeout.
An in-process timeout cannot fail cleanly on catastrophic backtracking: the
regex engine holds the GIL, so a pytest timeout plugin cannot interrupt it and
the whole run wedges. A subprocess timeout also works on Windows, where the
POSIX-only ``signal.SIGALRM`` approach silently does nothing.
"""

import inspect
import os
import subprocess
import sys

import pytest

_EVIL = r"(a+)+$"
_BAIT = "a" * 34 + "!"
_LIMIT = 20


def _run(code):
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import warnings;warnings.filterwarnings('ignore');" + code,
        ],
        capture_output=True,
        text=True,
        timeout=_LIMIT,
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)),
    )


def test_a_catastrophic_pattern_does_not_hang():
    """Completing or raising are both fine. Hanging past the bound is not."""
    code = (
        f"from nltk.stem.regexp import RegexpStemmer;"
        f"RegexpStemmer({_EVIL!r}).stem({_BAIT!r})"
    )
    try:
        _run(code)
    except subprocess.TimeoutExpired:
        pytest.fail("RegexpStemmer hung on a catastrophic pattern (ReDoS)")


def test_an_ordinary_pattern_still_stems():
    """Over-block control: bounding the engine must not change results."""
    code = (
        "from nltk.stem.regexp import RegexpStemmer;"
        "print(RegexpStemmer('ing$|s$|e$').stem('running'))"
    )
    result = _run(code)
    assert result.returncode == 0, result.stderr
    assert "runn" in result.stdout, result.stdout


def test_the_stemmer_routes_through_redos():
    """Pin the mechanism, not just the timing.

    A future edit could swap ``redos.compile`` back to ``re.compile`` and the
    timing test would still pass on a fast machine with a smaller bait string.
    """
    import nltk.stem.regexp

    source = inspect.getsource(nltk.stem.regexp)
    assert "redos.compile" in source, "RegexpStemmer no longer bounds its regex"


def test_a_catastrophic_PRECOMPILED_pattern_does_not_hang():
    """A pre-compiled ``re.Pattern`` (documented "str or regexp") must be
    re-hardened too. The old ``hasattr(...,'pattern')`` guard let a raw stdlib
    pattern through unbounded, so a caller handing in
    ``re.compile('(a+)+$')`` re-opened the ReDoS the string path had closed
    (CWE-1333 bypass; raw ``re`` ran ~24s on this bait).
    """
    code = (
        "import re;from nltk.stem.regexp import RegexpStemmer;"
        f"RegexpStemmer(re.compile({_EVIL!r})).stem({_BAIT!r})"
    )
    try:
        _run(code)
    except subprocess.TimeoutExpired:
        pytest.fail("RegexpStemmer hung on a pre-compiled catastrophic pattern")


def test_precompiled_pattern_flags_are_preserved():
    """Re-hardening a pre-compiled pattern must keep its flags (e.g. re.I)."""
    code = (
        "import re;from nltk.stem.regexp import RegexpStemmer;"
        "print(RegexpStemmer(re.compile('ING$', re.I)).stem('runnING'))"
    )
    result = _run(code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "runn", result.stdout


def test_precompiled_pattern_is_wrapped_as_timedpattern():
    """Both the string and the pre-compiled path must yield a bounded pattern."""
    import re

    from nltk.redos import TimedPattern
    from nltk.stem.regexp import RegexpStemmer

    assert isinstance(RegexpStemmer(re.compile(r"(a|a)*z"))._regexp, TimedPattern)
    assert isinstance(RegexpStemmer(r"(a|a)*z")._regexp, TimedPattern)


@pytest.fixture
def fast_default_timeout(monkeypatch):
    # Shorten the shared cap so the in-process hostile cases resolve quickly; the
    # monkeypatch is reverted after the test, so no module state leaks.
    from nltk import redos

    monkeypatch.setattr(redos, "DEFAULT_TIMEOUT", 0.4)


@pytest.mark.parametrize(
    "pattern,text",
    [
        (r"(a|a)*$", "a" * 80 + "!"),  # identical-branch alternation
        (r"(a|a)+b", "a" * 80),  # ``+`` variant
        (r"(.*a){25}z", "a" * 300),  # ``.*``-driven counted group
    ],
)
def test_hostile_pattern_over_single_long_token_is_bounded(
    pattern, text, fast_default_timeout
):
    # The stemmer applies its caller regex with ``.sub`` over the (single) token;
    # a hostile pattern against a long token must be wall-clock bounded, never
    # hang. Completing fast (engine collapse) or raising TimeoutError are both
    # bounded; a genuine hang would wedge here and the in-process short cap makes
    # the TimeoutError branch quick.
    import time

    from nltk.stem.regexp import RegexpStemmer

    start = time.perf_counter()
    try:
        RegexpStemmer(pattern).stem(text)
    except TimeoutError:
        pass
    assert time.perf_counter() - start < 2.0


def test_benign_large_token_still_stems_fast():
    import time

    from nltk.stem.regexp import RegexpStemmer

    stemmer = RegexpStemmer(r"ing$", min=4)
    start = time.perf_counter()
    # A long benign token: the suffix strip is linear and correct.
    assert stemmer.stem("a" * 100000 + "ing") == "a" * 100000
    assert time.perf_counter() - start < 2.0
