# Natural Language Toolkit: ReDoS on caller-supplied regexes
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Any API that compiles a CALLER's regex must bound it.

``nltk.redos.compile`` puts a wall-clock limit on matching. ``nltk.util.re_show``
takes both a pattern and a string from the caller and previously compiled the
pattern with a plain ``re.compile``, so a catastrophically backtracking pattern
such as ``(a+)+$`` against a 34-character bait string hung the interpreter
outright (CWE-1333). It now routes through ``nltk.redos.compile``.

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


def test_re_show_catastrophic_pattern_does_not_hang():
    """Completing or raising are both fine. Hanging is not."""
    code = f"from nltk.util import re_show; re_show({_EVIL!r}, {_BAIT!r})"
    try:
        _run(code)
    except subprocess.TimeoutExpired:
        pytest.fail("re_show hung on a catastrophic pattern (ReDoS)")


def test_re_show_ordinary_pattern_still_produces_the_right_answer():
    """Over-block control: bounding the engine must not change results."""
    code = "from nltk.util import re_show; re_show('o+','foo')"
    result = _run(code)
    assert result.returncode == 0, result.stderr
    assert "f{oo}" in result.stdout, result.stdout


def test_util_routes_through_redos():
    """Pin the mechanism, not just the timing.

    A future edit could swap redos.compile back to re.compile and the timing
    test would still pass on a fast machine with a smaller bait string.
    """
    import importlib
    import inspect

    # importlib, not "import nltk.util as util": the package star-imports
    # nltk.stem, whose own util module shadows the nltk.util ATTRIBUTE.
    module = importlib.import_module("nltk.util")
    assert module.__name__ == "nltk.util", module.__name__
    source = inspect.getsource(module)
    assert "redos.compile" in source, "nltk.util no longer bounds its regex"


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
