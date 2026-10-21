# Natural Language Toolkit: internals.read_str eval-boundary tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``nltk.internals.read_str`` hands a regex-delimited slice of grammar or tree
text to ``eval``. That is safe only while the slice is exactly one plain
string literal: ``_STRING_START_RE`` must admit no prefix that turns a
literal into code (an f-string evaluates its braces), and every malformed
literal must surface as ``ReadError`` rather than an interpreter error
(CWE-95 boundary, found by the line sweep of every eval in the package)."""

import os
import tempfile

import pytest

from nltk.internals import ReadError, read_str
from nltk.test.unit import timing

_INJECTION = "{__import__('os').system('touch %s')}"


@pytest.fixture
def canary():
    fd, path = tempfile.mkstemp(prefix="nltk_read_str_")
    os.close(fd)
    os.remove(path)
    # forward slashes: a Windows path's backslashes would themselves be escape
    # sequences inside the literal (see test_windows_path_inside_literal_fails_closed)
    yield path.replace("\\", "/")
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.parametrize(
    "prefix", ["f", "F", "rf", "Rf", "fr", "fR", "RF", "FR", "b", "B", "br", "rb", "t"]
)
def test_code_bearing_prefixes_never_reach_eval(prefix, canary):
    with pytest.raises(ReadError):
        read_str(prefix + '"' + _INJECTION % canary + '"', 0)
    assert not os.path.exists(canary)


@pytest.mark.parametrize("prefix", ["", "u", "U", "r", "R"])
def test_plain_prefixes_yield_the_literal_text(prefix, canary):
    # braces inside a plain literal are text, never evaluated
    value, end = read_str(prefix + '"' + _INJECTION % canary + '"', 0)
    assert value.startswith("{__import__")
    assert end == len(prefix) + len(_INJECTION % canary) + 2
    assert not os.path.exists(canary)


@pytest.mark.parametrize(
    "payload",
    [
        '"" + __import__("os").system("id") + ""',
        "'a' if __import__('os').system('id') else 'b'",
        '"\\x22 + __import__("os").system("id") + \\x22"',
    ],
)
def test_expression_after_the_literal_is_not_consumed(payload):
    # eval sees only the first delimited literal; the rest stays unread text
    value, end = read_str(payload, 0)
    assert isinstance(value, str)
    quote = payload[0]
    assert end == payload.index(quote, 1) + 1
    assert "__import__" not in value or value.startswith('" + ')


@pytest.mark.parametrize(
    "malformed", ['"a\nb"', 'ur"x"', '"\\N{NOT A REAL NAME}"', '"unterminated']
)
def test_malformed_literals_fail_closed_with_read_error(malformed):
    # a raw newline or an invalid prefix is a SyntaxError inside eval, an
    # invalid escape a ValueError; both must surface as the parser's ReadError
    with pytest.raises(ReadError):
        read_str(malformed, 0)


def test_windows_path_inside_literal_fails_closed():
    # a backslash path such as C:\\Users\\x inside the literal is a malformed
    # \\U escape to eval; it must surface as ReadError, never as SyntaxError
    # (the Windows CI runner found exactly this with a temp-dir canary)
    with pytest.raises(ReadError):
        read_str('"touch C:\\Users\\runner\\canary"', 0)


def test_benign_escapes_still_decode():
    assert read_str(r'"tab\tnew\nline"', 0)[0] == "tab\tnew\nline"
    assert read_str("'it''s'", 0) == ("it", 4)
    assert read_str('"""triple"""', 0)[0] == "triple"


# === The rest of the surface: positions, input types and what reaches the parser ===


@pytest.mark.parametrize("position", [1.0, "0", None, [0], b"0", 0j])
def test_non_integer_positions_are_a_type_error(position):
    with pytest.raises(TypeError, match="start_position must be an int"):
        read_str('"abc"', position)


@pytest.mark.parametrize("position", [-1, -100, -(10**9)])
def test_negative_positions_are_refused_as_no_open_quote(position):
    # -1 and -100 used to disagree (a garbage slice vs a silent re-parse from
    # 0) because the regex clamps a negative pos but the slice indexes from the
    # end; both are now "no literal starts here", position preserved.
    with pytest.raises(ReadError) as info:
        read_str('"abc"', position)
    assert info.value.expected == "open quote" and info.value.position == position


@pytest.mark.parametrize("position", [5, 6, 10**9])
def test_positions_past_the_end_are_refused(position):
    with pytest.raises(ReadError, match="open quote"):
        read_str('"abc"', position)


def test_index_like_positions_are_accepted():
    class Index:
        def __index__(self):
            return 4

    assert read_str('abc "x"', Index()) == ("x", 7)
    assert read_str(' "b"', True) == ("b", 4)  # bool is an int: position 1


@pytest.mark.parametrize("source", [b'"abc"', bytearray(b'"abc"'), None, 1, ['"abc"']])
def test_non_str_input_is_a_type_error(source):
    with pytest.raises(TypeError, match="read_str expects a str"):
        read_str(source, 0)


@pytest.fixture
def parser_spy(monkeypatch):
    """Record exactly what read_str hands to ast.literal_eval, and make any
    other evaluation path fail loudly."""
    import builtins

    from nltk import internals

    seen = []
    real = internals.ast.literal_eval

    def _record(text):
        seen.append(text)
        return real(text)

    def _boom(*a, **k):
        raise AssertionError("eval/exec reached")

    monkeypatch.setattr(internals.ast, "literal_eval", _record)
    monkeypatch.setattr(builtins, "eval", _boom)
    monkeypatch.setattr(builtins, "exec", _boom)
    return seen


def test_str_subclass_cannot_hand_the_parser_different_text(parser_spy):
    class Lying(str):
        def __getitem__(self, item):
            return "{'pwned': 1}"

        def __str__(self):
            return "'lie'"

        def split(self, *a, **k):
            raise AssertionError("split called")

        def strip(self, *a, **k):
            raise AssertionError("strip called")

        def __eq__(self, other):
            return True

        __hash__ = str.__hash__

    value, end = read_str(Lying('"abc" + x'), 0)
    assert (value, end) == ("abc", 5)
    assert parser_spy == ['"abc"'] and type(parser_spy[0]) is str


@pytest.mark.parametrize(
    "prefix",
    [
        "b",
        "B",
        "br",
        "rb",
        "Rb",
        "bR",
        "BR",
        "f",
        "F",
        "fr",
        "rf",
        "Rf",
        "fR",
        "t",
        "tr",
        "rt",
        "x",
        "s",
        "ru",
        "Ru",
        "uu",
        "rr",
        "urr",
        "bu",
    ],
)
def test_every_code_bearing_or_invalid_prefix_never_reaches_the_parser(
    prefix, parser_spy
):
    with pytest.raises(ReadError):
        read_str(prefix + '"{__import__(1)}"', 0)
    assert parser_spy == []


@pytest.mark.parametrize("prefix", ["", "u", "U", "r", "R", "ur", "UR", "uR", "Ur"])
def test_every_plain_prefix_is_delimited_and_only_that_slice_is_parsed(
    prefix, parser_spy
):
    source = prefix + '"a\\tb" + rest'
    try:
        value, end = read_str(source, 0)
    except ReadError:
        # "ur" is not a Python 3 prefix: the slice reached the parser and was
        # refused there, never evaluated as anything else
        assert prefix.lower() == "ur"
    else:
        assert type(value) is str and end == len(prefix) + 6
    assert parser_spy == [source[: len(prefix) + 6]]


@pytest.mark.parametrize(
    "source,expected,end",
    [
        ('"""a"b"""', 'a"b', 9),
        ("'''a''b'''", "a''b", 10),
        ('"a\'b"', "a'b", 5),
        ("'a\"b'", 'a"b', 5),
        ('"""a\\""""', 'a"', 9),
        ('"a\\"b"', 'a"b', 6),
        ('""', "", 2),
        ('""""""', "", 6),
        ('"\\x00"', chr(0), 6),
        ('"a\\x00b"', "a" + chr(0) + "b", 8),
        ('"\\udcff"', chr(0xDCFF), 8),
        ('"\\ud800\\udc00"', chr(0xD800) + chr(0xDC00), 14),
        ('"\\N{LATIN SMALL LETTER A}"', "a", 26),
        ('"\\u00e9"', chr(0xE9), 8),
        ('"\\\\"', "\\", 4),
        ("r'\\'", None, None),
    ],
)
def test_nested_and_triple_quotes_and_odd_escapes_stay_plain_text(
    source, expected, end, parser_spy
):
    if expected is None:
        with pytest.raises(ReadError, match="close quote"):
            read_str(source, 0)
        assert parser_spy == []
        return
    value, got_end = read_str(source, 0)
    assert type(value) is str and value == expected and got_end == end
    assert parser_spy == [source[:end]]


@pytest.mark.parametrize(
    "source",
    [
        '"a" + __import__("os").system("id")',
        "'a'.__class__.__mro__",
        '"a"; __import__("os")',
        '"a"\n__import__("os")',
        '"a"[0].upper()',
        "'a' if __import__('os') else 'b'",
        '"" or __import__("os")',
        '"\\"" + __import__("os").name + "\\""',
    ],
)
def test_a_literal_followed_by_an_expression_parses_only_the_literal(
    source, parser_spy
):
    value, end = read_str(source, 0)
    assert type(value) is str
    assert end == source.index(source[0], 1) + 1 or source.startswith('"\\""')
    assert len(parser_spy) == 1 and parser_spy[0] == source[:end]
    assert "__import__" not in parser_spy[0]


def test_long_literals_are_linear_and_bounded():
    # No cap is imposed: the work is linear in an already in-memory input the
    # caller owns, so it is bounded by that input; pinned generously.
    escaped = '"' + "\\\\" * 100000 + '"'
    plain = '"' + "x" * 1000000 + '"'
    with timing.budget(5.0):
        assert read_str(escaped, 0) == ("\\" * 100000, len(escaped))
        assert read_str(plain, 0) == ("x" * 1000000, len(plain))


def test_the_return_type_guard_has_teeth(monkeypatch):
    # If the parser ever handed back something other than a str for the
    # delimited slice, read_str must refuse rather than return it.
    from nltk import internals

    monkeypatch.setattr(internals.ast, "literal_eval", lambda text: {"pwned": 1})
    with pytest.raises(ReadError, match="valid string literal"):
        read_str('"abc"', 0)
