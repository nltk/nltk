# Natural Language Toolkit: termsec terminal-injection attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Adversarial coverage for ``nltk.termsec`` against the full known terminal- and
spreadsheet-injection surface (CWE-150 / 1007 / 1236), exercising the sanitiser
directly (no mocks). Each attack must be neutralised; every legitimate string
(including balanced bidi, joiners and non-ASCII) must pass through unchanged.

All invisible characters are constructed with ``chr(0x...)`` so the source stays
fully readable and cannot be silently mangled by an editor or a merge.
"""

import pytest

from nltk.termsec import (
    _bidi_is_balanced,
    sanitize_csv_field,
    sanitize_terminal,
)

ESC, CSI8 = "\x1b", "\x9b"
RLO, LRO = chr(0x202E), chr(0x202D)
LRE, RLE, PDF = chr(0x202A), chr(0x202B), chr(0x202C)
LRI, RLI, FSI, PDI = chr(0x2066), chr(0x2067), chr(0x2068), chr(0x2069)
LRM, RLM, ALM = chr(0x200E), chr(0x200F), chr(0x061C)  # direction marks (legit)
LSEP, PSEP = chr(0x2028), chr(0x2029)
ZWSP, WJ, ZWNBSP = chr(0x200B), chr(0x2060), chr(0xFEFF)
IAA, IAT = chr(0xFFF9), chr(0xFFFB)  # interlinear annotation anchor / terminator
DEPR = chr(0x206A)  # deprecated format (inhibit symmetric swapping)
TAG_A, TAG_B = chr(0xE0041), chr(0xE0042)  # Unicode Tags block (invisible smuggle)
ZWJ, ZWNJ = chr(0x200D), chr(0x200C)  # legitimate joiners (must pass through)

_ESCAPED = {
    0x202E,
    0x202D,
    0x2028,
    0x2029,
    0x200B,
    0x2060,
    0xFEFF,
    0xFFF9,
    0xFFFB,
    0x206A,
}


def _has_live_control(s):
    for ch in s:
        cp = ord(ch)
        if ch in "\t\n":
            continue
        if cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F:
            return True
        if cp in _ESCAPED or 0xE0000 <= cp <= 0xE007F:
            return True
    return False


ATTACKS = {
    "csi-color": ESC + "[31mred" + ESC + "[0m",
    "csi-clear-screen": ESC + "[2J",
    "csi-cursor-home": ESC + "[H",
    "c1-8bit-csi": CSI8 + "31m",
    "osc8-hyperlink": ESC + "]8;;http://evil" + ESC + "\\click",
    "osc52-clipboard-write": ESC + "]52;c;ZXZpbA==\x07",
    "query-da-stdin-inject": ESC + "[c",
    "query-dsr": ESC + "[6n",
    "answerback-enq": "\x05",
    "carriage-return-overwrite": "safe\rEVIL",
    "backspace-erase": "rm -rf\x08\x08 ls",
    "bidi-rlo-override": "user" + RLO + "gnp.txt",
    "bidi-crossed": LRE + LRI + PDF + PDI,
    "bidi-unterminated": LRE + "evil",
    "bidi-fsi-unterminated": FSI + "evil",
    "bidi-override-in-embedding": LRE + RLO + "x" + PDF,
    "bidi-extra-close": "x" + PDF,
    "mixed-esc-bidi-tag": ESC + "[31m" + RLO + "x" + TAG_A,
    "line-separator": "safe" + LSEP + "EVIL",
    "paragraph-separator": "safe" + PSEP + "EVIL",
    "zero-width-space": "e" + ZWSP + "vil",
    "word-joiner": "e" + WJ + "vil",
    "zwnbsp": "e" + ZWNBSP + "vil",
    "tag-smuggling": "hi" + TAG_A + TAG_B,
    "interlinear": "a" + IAA + "b" + IAT + "c",
    "deprecated-format": "a" + DEPR + "b",
}

LEGIT = {
    "ascii": "hello world",
    "tab-newline": "a\tb\nc",
    "accented": "café résumé naïve",
    "cjk": "日本語のテキスト",
    "balanced-lre-pdf": "x" + LRE + "hello" + PDF + "y",
    "nested-lre-lri": LRE + LRI + "inner" + PDI + PDF,
    "arabic": "مرحبا بالعالم",
    "zwj-emoji": "\U0001f468" + ZWJ + "\U0001f469",
    "zwnj-persian": "پ" + ZWNJ + "د",
    "bidi-marks": LRM + "a" + RLM + "b" + ALM + "c",
    "balanced-rli-embedded": RLI + LRE + "x" + PDF + PDI,
}


class TestTerminalInjectionNeutralized:
    @pytest.mark.parametrize("name", list(ATTACKS))
    def test_attack_is_neutralized(self, name):
        assert not _has_live_control(sanitize_terminal(ATTACKS[name]))


class TestLegitimateTextPreserved:
    @pytest.mark.parametrize("name", list(LEGIT))
    def test_legit_unchanged(self, name):
        assert sanitize_terminal(LEGIT[name]) == LEGIT[name]


class TestBidiStrictNesting:
    def test_proper_nesting_is_balanced(self):
        assert _bidi_is_balanced(LRE + LRI + "x" + PDI + PDF)

    def test_crossed_nesting_is_rejected(self):
        # LRE LRI PDF PDI: two independent counters wrongly accept this crossing.
        assert not _bidi_is_balanced(LRE + LRI + PDF + PDI)

    def test_crossed_nesting_is_neutralized(self):
        assert not _has_live_control(sanitize_terminal(LRE + LRI + PDF + PDI))


class TestCsvInjectionWired:
    def test_sanitize_csv_field_neutralizes_formula_and_control(self):
        out = sanitize_csv_field("=cmd|'/c calc'!A1" + ESC + "[31m")
        assert out.startswith("'=")  # formula lead defused
        assert ESC not in out  # control neutralised

    def test_negative_number_keeps_sign(self):
        assert sanitize_csv_field("-3.5") == "-3.5"
