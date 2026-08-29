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
