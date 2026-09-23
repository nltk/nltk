# Natural Language Toolkit: terminal-injection print-sink tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``nltk.termsec.safe_print`` is the sink primitive every untrusted-text print
site is meant to route through, so a crafted corpus token / package id / tweet
body carrying an ANSI escape, C1 control, bidi override or invisible smuggling
character can never reach the terminal live (CWE-150 / 1007 / 1236).

These tests drive the real ``safe_print`` (captured stdout, not a mock) and pin
three properties: an injection payload is emitted only in neutralised form, the
sep/end terminators are sanitised too, and clean text is emitted byte-identically
so ``safe_print`` is a true drop-in for ``print``."""

import pytest

from nltk.termsec import safe_print

ESC = "\x1b"
RLO = chr(0x202E)

# Codepoints a terminal would act on / that would corrupt or crash the write; a
# neutralised sink must leave NONE of them in the emitted bytes. Derived here so
# the check does not just mirror nltk.termsec.
_ALWAYS_FORMAT = (
    {
        0x00AD,
        0x115F,
        0x1160,
        0x3164,
        0xFFA0,
        0x17B4,
        0x17B5,
        0x180E,
        0x2028,
        0x2029,
        0x200B,
        0x2060,
        0xFEFF,
        0x2061,
        0x2062,
        0x2063,
        0x2064,
        0x2065,
        0xFFF9,
        0xFFFA,
        0xFFFB,
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,
        0x2066,
        0x2067,
        0x2068,
        0x2069,
        # direction marks: flagged here like the attack-matrix detector, since
        # every injection payload below uses bidi only in unbalanced form
        0x200E,
        0x200F,
        0x061C,
    }
    | set(range(0xFFF0, 0xFFF9))
    | set(range(0x1BCA0, 0x1BCA4))
    | set(range(0x206A, 0x2070))
)


def _dangerous_cp(cp):
    return (
        (cp < 0x20 and cp not in (0x09, 0x0A))
        or cp == 0x7F
        or 0x80 <= cp <= 0x9F
        or cp in _ALWAYS_FORMAT
        or 0xE0000 <= cp <= 0xE0FFF
        or 0x1D173 <= cp <= 0x1D17A
        or 0xD800 <= cp <= 0xDFFF
        or 0xFDD0 <= cp <= 0xFDEF
        or (cp & 0xFFFE) == 0xFFFE
    )


def _has_live_control(s):
    return any(_dangerous_cp(ord(ch)) for ch in s)


INJECTIONS = [
    ESC + "[2J",  # clear screen
    ESC + "[31mred" + ESC + "[0m",  # SGR colour
    ESC + "]0;pwned\x07",  # OSC window-title set
    ESC + "]52;c;ZXZpbA==\x07",  # OSC-52 clipboard write
    ESC + "]8;;http://evil" + ESC + "\\link",  # OSC-8 hyperlink
    "\x9b31m",  # 8-bit CSI
    "\x9d0;t\x07",  # 8-bit OSC
    "line\rSPOOFED",  # carriage-return overwrite
    "safe\x08\x08evil",  # backspace erase
    "\x05",  # answerback ENQ
    "user" + RLO + "gnp.txt",  # bidi override
    "e" + chr(0x200B) + "vil",  # zero-width space
    "in" + chr(0x00AD) + "voice",  # soft hyphen
    "hi" + chr(0xE0041) + chr(0xE0042),  # tags-block smuggle
    "a" + chr(0xE0100) + "b",  # variation-selector supplement
    "a" + chr(0xFFFE) + "b",  # noncharacter
    "note" + chr(0x1D173) + "hidden",  # musical-symbol format control (invisible)
    "a" + chr(0xE01F0) + "b",  # reserved plane-14 default-ignorable
    "pkg" + chr(0xD800) + "evil",  # lone surrogate (would crash a naive print)
]

CLEAN = [
    "ordinary café text 3.14",
    "unicode: 模型 naïve 😀",
    "❤" + chr(0xFE0F),  # emoji with variation selector
    "\U0001f468" + chr(0x200D) + "\U0001f469",  # ZWJ family emoji
    "مرحبا بالعالم",  # arabic (no explicit controls)
    "with\ttabs\tand spaces",
]


class TestSafePrintNeutralisesInjection:
    @pytest.mark.parametrize("payload", INJECTIONS)
    def test_no_live_control_reaches_stdout(self, payload, capsys):
        safe_print(payload)
        out = capsys.readouterr().out
        assert not _has_live_control(out), f"live control emitted for {payload!r}"

    def test_object_value_with_crafted_str_is_neutralised(self, capsys):
        # non-string values are coerced with str() INSIDE the sink, so a
        # crafted __str__ cannot smuggle a live sequence past it
        class EscObj:
            def __str__(self):
                return "\x1b[2J" + chr(0x202E) + "evil"

        safe_print(EscObj())
        assert not _has_live_control(capsys.readouterr().out)


class TestSafePrintTerminatorsSanitised:
    def test_sep_and_end_are_sanitised(self, capsys):
        safe_print("a", "b", sep=ESC + "[31m", end=ESC + "]0;x\x07\n")
        out = capsys.readouterr().out
        assert not _has_live_control(out)
        assert "a" in out and "b" in out

    def test_sep_none_keeps_default(self, capsys):
        safe_print("a", "b", sep=None)
        assert capsys.readouterr().out == "a b\n"


class TestSafePrintIdentityForCleanText:
    @pytest.mark.parametrize("text", CLEAN)
    def test_clean_text_emitted_unchanged(self, text, capsys):
        safe_print(text)
        assert capsys.readouterr().out == text + "\n"

    def test_detector_has_teeth(self):
        # if the detector missed these, the neutralisation asserts pass vacuously
        assert _has_live_control(ESC)
        assert _has_live_control(chr(0xD800))
        assert not _has_live_control("clean café 😀")
