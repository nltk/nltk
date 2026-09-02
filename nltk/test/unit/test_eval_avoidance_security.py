# Natural Language Toolkit: eval-avoidance security tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk.internals.read_str parses a caller-supplied quoted string literal. It
now uses ast.literal_eval (not eval), so an expression / f-string can never
execute code even if the string-start pattern were ever loosened. TextTiling's
smoothing resolves its numpy window via getattr on an allowlisted name, not
eval."""

import pytest

from nltk.internals import ReadError, read_str


@pytest.mark.parametrize(
    "literal,expected",
    [
        ('"hello"', "hello"),
        ("'world'", "world"),
        ('r"raw\\n"', "raw\\n"),
        ('u"caf\\u00e9"', "café"),
        ('"""triple"""', "triple"),
    ],
)
def test_read_str_parses_string_literals(literal, expected):
    assert read_str(literal, 0)[0] == expected


@pytest.mark.parametrize(
    "hostile",
    [
        "f\"{__import__('os').system('echo pwn')}\"",  # f-string (blocked at regex + literal_eval)
        "__import__('os').system('id')",  # bare expression (no open quote)
    ],
)
def test_read_str_never_executes_an_expression(hostile):
    # The string-start regex rejects a non-quote start (ReadError); an f-string
    # is also refused by literal_eval. Never code execution.
    with pytest.raises(ReadError):
        read_str(hostile, 0)


def test_read_str_truncates_at_close_quote_ignoring_trailing_expression():
    # A leading literal followed by an expression: read_str returns ONLY the
    # literal and never evaluates the trailing "+ __import__(...)" expression.
    value, end = read_str('"a" + __import__("os").name', 0)
    assert value == "a" and end == 3


def test_texttiling_smooth_uses_no_eval_and_all_windows_work():
    import numpy

    from nltk.tokenize.texttiling import smooth

    x = numpy.array([float(i % 5) for i in range(60)])
    for window in ("flat", "hanning", "hamming", "bartlett", "blackman"):
        y = smooth(x, window_len=11, window=window)
        assert len(y) == len(x) and numpy.all(numpy.isfinite(y))
    # An out-of-allowlist window is refused before any resolution.
    with pytest.raises(ValueError):
        smooth(x, window_len=11, window="__import__")
