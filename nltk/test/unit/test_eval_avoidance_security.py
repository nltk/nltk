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


# === texttiling.smooth: the window name is judged on its real characters ===


class _LyingWindow(str):
    """Reports equal to an allowlisted name while its real characters name
    another numpy function; ``in`` and ``==`` both go through this __eq__."""

    def __eq__(self, other):
        if other == "hanning":
            return True
        if other == "flat":
            return False
        return str.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash("hanning")


@pytest.fixture
def numpy_zeros_spy(monkeypatch):
    import numpy

    calls = []

    def _spy(*a, **k):
        calls.append(a)
        raise AssertionError("numpy.zeros reached through smooth()")

    monkeypatch.setattr(numpy, "zeros", _spy)
    return calls


def test_texttiling_lying_str_subclass_cannot_reach_another_numpy_function(
    numpy_zeros_spy,
):
    import numpy

    from nltk.tokenize.texttiling import smooth

    x = numpy.array([float(i % 5) for i in range(60)])
    assert _LyingWindow("zeros") in ["flat", "hanning"]  # the lie works on `in`
    with pytest.raises(ValueError, match="Window is on of"):
        smooth(x, window_len=11, window=_LyingWindow("zeros"))
    assert numpy_zeros_spy == []


class _LyingStr(str):
    def __str__(self):
        return "hanning"


@pytest.mark.parametrize(
    "window",
    [
        _LyingStr("zeros"),
        b"hanning",
        bytearray(b"hanning"),
        None,
        1,
        ["hanning"],
        ("hanning",),
        "__import__",
        "os.system",
        "numpy.hanning",
        "hanning ",
        " flat",
        "Hanning",
        "HANNING",
        "flat" + chr(0),
        "hanning\n",
        "",
        "zeros",
        "ones",
        "kaiser",
        "__class__",
        "sum",
    ],
    ids=lambda w: repr(w)[:18],
)
def test_texttiling_attribute_shaped_and_non_str_windows_are_refused(
    window, numpy_zeros_spy
):
    import numpy

    from nltk.tokenize.texttiling import smooth

    x = numpy.array([float(i % 5) for i in range(60)])
    with pytest.raises(ValueError, match="Window is on of"):
        smooth(x, window_len=11, window=window)
    assert numpy_zeros_spy == []


def test_texttiling_str_subclass_with_honest_characters_still_works():
    # numpy.str_ is a str subclass; a caller reading the window name out of a
    # numpy array must keep working, since the real characters are judged.
    import numpy

    from nltk.tokenize.texttiling import smooth

    x = numpy.array([float(i % 5) for i in range(60)])
    for name in ("flat", "hanning", "hamming", "bartlett", "blackman"):
        assert len(smooth(x, window_len=11, window=numpy.str_(name))) == len(x)


def test_texttiling_every_window_on_real_brown_gap_scores():
    import numpy

    from nltk.corpus import brown
    from nltk.tokenize.texttiling import TextTilingTokenizer, smooth

    tt = TextTilingTokenizer(demo_mode=True)
    gap_scores, smoothed, depth, boundaries = tt.tokenize(brown.raw()[:6000])
    assert len(gap_scores) > 12 and len(smoothed) == len(gap_scores)
    assert all(numpy.isfinite(smoothed))
    x = numpy.array(gap_scores)
    for name in ("flat", "hanning", "hamming", "bartlett", "blackman"):
        y = smooth(x, window_len=tt.smoothing_width + 1, window=name)
        assert len(y) == len(x) and numpy.all(numpy.isfinite(y))
    assert list(smooth(x, window_len=tt.smoothing_width + 1)) == list(smoothed)
