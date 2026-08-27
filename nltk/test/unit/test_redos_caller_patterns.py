# Natural Language Toolkit: ReDoS on caller-supplied regexes
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Any API that compiles a CALLER's regex must bound it.

``nltk.redos.compile`` puts a wall-clock limit on matching. Most regex entry
points already use it; two did not, and both hung the interpreter outright on
``(a+)+$`` against a 34-character bait string:

* ``RegexpStemmer(pattern)`` -- pattern and word are both caller-supplied
* ``nltk.util.re_show(pattern, string)`` -- likewise

These run in a SUBPROCESS with a timeout. An in-process test cannot fail
cleanly on catastrophic backtracking: the regex engine does not release the GIL,
so a pytest timeout plugin cannot interrupt it and the whole run wedges. That is
also why a hang must be asserted as a timeout rather than measured with a clock.
"""

import os
import subprocess
import sys

import pytest

_EVIL = r"(a+)+$"
_BAIT = "a" * 34 + "!"
_LIMIT = 20


def _run(code):
    return subprocess.run(
        [sys.executable, "-c", "import warnings;warnings.filterwarnings('ignore');" + code],
        capture_output=True,
        text=True,
        timeout=_LIMIT,
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)),
    )


@pytest.mark.parametrize(
    "code, label",
    [
        (
            f"from nltk.stem.regexp import RegexpStemmer;"
            f"RegexpStemmer({_EVIL!r}).stem({_BAIT!r})",
            "RegexpStemmer",
        ),
        (
            f"from nltk.util import re_show; re_show({_EVIL!r}, {_BAIT!r})",
            "re_show",
        ),
        (
            f"from nltk.tokenize import RegexpTokenizer;"
            f"RegexpTokenizer({_EVIL!r}).tokenize({_BAIT!r})",
            "RegexpTokenizer",
        ),
        (
            f"from nltk.tag import RegexpTagger;"
            f"RegexpTagger([({_EVIL!r},'X')]).tag([{_BAIT!r}])",
            "RegexpTagger",
        ),
    ],
)
def test_a_catastrophic_pattern_does_not_hang(code, label):
    """Completing or raising are both fine. Hanging is not."""
    try:
        _run(code)
    except subprocess.TimeoutExpired:
        pytest.fail(f"{label} hung on a catastrophic pattern (ReDoS)")


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            "from nltk.stem.regexp import RegexpStemmer;"
            "print(RegexpStemmer('ing$|s$|e$').stem('running'))",
            "runn",
        ),
        ("from nltk.util import re_show; re_show('o+','foo')", "f{oo}"),
        (
            "from nltk.tokenize import RegexpTokenizer;"
            "print(RegexpTokenizer(r'\\w+').tokenize('hi there'))",
            "['hi', 'there']",
        ),
    ],
    ids=["stemmer", "re_show", "tokenizer"],
)
def test_ordinary_patterns_still_produce_the_right_answer(code, expected):
    """Over-block control: bounding the engine must not change results."""
    result = _run(code)
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout, result.stdout


def test_the_bounded_modules_route_through_redos():
    """Pin the mechanism, not just the timing.

    A future edit could swap redos.compile back to re.compile and these timing
    tests would still pass on a fast machine with a smaller bait string.
    """
    import importlib
    import inspect

    # importlib, not "import nltk.util as util": the package star-imports
    # nltk.stem, whose own util module shadows the nltk.util ATTRIBUTE, so the
    # plain import silently hands back nltk.stem.util instead.
    for name in ("nltk.stem.regexp", "nltk.util"):
        module = importlib.import_module(name)
        assert module.__name__ == name, f"{name} resolved to {module.__name__}"
        source = inspect.getsource(module)
        assert "redos.compile" in source, f"{name} no longer bounds its regex"
