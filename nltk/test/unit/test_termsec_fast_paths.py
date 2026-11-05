# Natural Language Toolkit: termsec fast-path equivalence tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The cheaper clean-text check in nltk.termsec must decide as before.

``_is_clean`` used to search a non-ASCII text for each of the 246 printable
but dangerous characters, about ten microseconds a call for a short token, so
``safe_print`` of a non-ASCII word cost twenty times ``print``. It now searches
only the characters no greater than the text's largest. ``safe_print`` also no
longer re-sanitises its default separators. These tests compare the new check
with the full search on every single code point and on every dangerous
character set against a range of larger characters, both line modes.
"""

import io

import pytest

from nltk.termsec import (
    _PRINTABLE_BUT_DANGEROUS,
    _escape_scan,
    _is_clean,
    safe_print,
    sanitize_terminal,
)


def _reference(text, single_line):
    """The check as it was: every dangerous character searched."""
    probe = text if single_line else text.replace("\t", "").replace("\n", "")
    if not probe.isprintable():
        return False
    if text.isascii():
        return True
    return not any(c in text for c in _PRINTABLE_BUT_DANGEROUS)


@pytest.mark.parametrize("single_line", [False, True])
def test_every_code_point_alone(single_line):
    for cp in range(0x110000):
        text = chr(cp)
        assert _is_clean(text, single_line) == _reference(text, single_line), hex(cp)


_TOPS = [
    0x7E,
    0xE9,
    0x115E,
    0x115F,
    0x1160,
    0x17B3,
    0x17B6,
    0x3163,
    0x3165,
    0x65E5,
    0xFF9F,
    0xFFA0,
    0xFFA1,
    0xFFFD,
    0x1F600,
    0xE00FF,
    0xE0100,
    0xE01EF,
    0xE01F0,
    0x10FFFD,
]


@pytest.mark.parametrize("single_line", [False, True])
def test_dangerous_characters_beside_larger_and_smaller_ones(single_line):
    """Each dangerous character, and its neighbours, next to text whose
    largest character falls below, on and above it."""
    probes = set()
    for c in _PRINTABLE_BUT_DANGEROUS:
        probes.update({ord(c) - 1, ord(c), ord(c) + 1})
    for cp in sorted(probes):
        for top in _TOPS:
            for text in (
                chr(cp) + chr(top),
                chr(top) + "ab" + chr(cp),
                "caf\u00e9 " + chr(cp) + "\t\n",
            ):
                assert _is_clean(text, single_line) == _reference(text, single_line), (
                    hex(cp),
                    hex(top),
                )
                assert sanitize_terminal(text, single_line=single_line) == _escape_scan(
                    text, single_line
                )


def test_default_separators_are_printed_as_before():
    """The default sep and end, and equal ones passed explicitly, print the
    same bytes; any other separator is still sanitised."""
    outs = []
    for kwargs in ({}, {"sep": " ", "end": "\n"}, {"sep": "", "end": ""}):
        buf = io.StringIO()
        safe_print("a", "b\x1b[2J", file=buf, **kwargs)
        outs.append(buf.getvalue())
    assert outs[0] == outs[1] == "a b\\x1b[2J\n"
    assert outs[2] == "ab\\x1b[2J"
    buf = io.StringIO()
    safe_print("a", "b", sep="\x1b[31m", end="\u202e\n", file=buf)
    assert buf.getvalue() == "a\\x1b[31mb\\u202e\n"
