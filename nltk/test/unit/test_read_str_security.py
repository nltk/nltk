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
