# Natural Language Toolkit: termsec terminal-injection attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Adversarial coverage for ``nltk.termsec`` against the full known terminal- and
spreadsheet-injection surface (CWE-150 / 1007 / 1236), exercising the sanitiser
directly (no mocks). Each attack must be neutralised; every legitimate string
(including balanced bidi, joiners, emoji variation/ZWJ sequences and non-ASCII)
must pass through unchanged.

All invisible characters are constructed with ``chr(0x...)`` so the source stays
fully readable and cannot be silently mangled by an editor or a merge. The
``_has_live_control`` detector is re-derived independently of ``nltk.termsec`` so
a regression that stops escaping a class is caught rather than mirrored away.
"""

import pytest

from nltk.termsec import _bidi_is_balanced, sanitize_csv_field, sanitize_terminal

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
SHY = chr(0x00AD)  # soft hyphen (invisible)
IMATH = chr(0x2062)  # invisible times
HFILL = chr(0x3164)  # hangul filler (invisible)
MVS = chr(0x180E)  # mongolian vowel separator (zero-width)
VS_SUP = chr(0xE0100)  # variation selector supplement (steganography channel)
VS16 = chr(0xFE0F)  # emoji-presentation selector (legit, must pass)
SURR = chr(0xD800)  # lone surrogate (crashes a naive write)
NONCHAR = chr(0xFFFE)  # a Unicode noncharacter

# The codepoints that MUST NOT survive sanitisation, re-derived here independently
# of nltk.termsec so this detector is a real cross-check, not a mirror. Bidi
# embeddings/isolates/marks are included because every ATTACK payload below is
# unbalanced or an override, so the sanitiser escapes them all.
_BIDI_CONTROLS = {
    0x202A,
    0x202B,
    0x202C,
    0x202D,
    0x202E,
    0x2066,
    0x2067,
    0x2068,
    0x2069,
    0x200E,
    0x200F,
    0x061C,
}
_ALWAYS_FORMAT = {
    0x00AD,
    0x115F,
    0x1160,
    0x3164,
    0xFFA0,
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
    0xFFF9,
    0xFFFA,
    0xFFFB,
} | set(range(0x206A, 0x2070))


def _dangerous_cp(cp):
    return (
        (cp < 0x20 and cp not in (0x09, 0x0A))
        or cp == 0x7F
        or 0x80 <= cp <= 0x9F
        or cp in _BIDI_CONTROLS
        or cp in _ALWAYS_FORMAT
        or 0xE0000 <= cp <= 0xE01EF
        or 0xD800 <= cp <= 0xDFFF
        or 0xFDD0 <= cp <= 0xFDEF
        or (cp & 0xFFFE) == 0xFFFE
    )


def _has_live_control(s):
    return any(_dangerous_cp(ord(ch)) for ch in s)


ATTACKS = {
    "csi-color": ESC + "[31mred" + ESC + "[0m",
    "csi-clear-screen": ESC + "[2J",
    "csi-cursor-home": ESC + "[H",
    "csi-alt-screen": ESC + "[?1049h",
    "csi-scroll-region": ESC + "[1;10r",
    "c1-8bit-csi": CSI8 + "31m",
    "c1-8bit-dcs": chr(0x90) + "q",
    "c1-8bit-osc": chr(0x9D) + "0;t\x07",
    "c1-8bit-apc": chr(0x9F) + "cmd",
    "c1-8bit-pm": chr(0x9E) + "x",
    "c1-8bit-sos": chr(0x98) + "x",
    "c1-nel": "line1" + chr(0x85) + "line2",
    "dcs-decrqss": ESC + "P$qm" + ESC + "\\",
    "apc-string": ESC + "_payload" + ESC + "\\",
    "pm-string": ESC + "^payload" + ESC + "\\",
    "sos-string": ESC + "Xpayload" + ESC + "\\",
    "ris-full-reset": ESC + "c",
    "osc4-color": ESC + "]4;0;#000000\x07",
    "osc8-hyperlink": ESC + "]8;;http://evil" + ESC + "\\click",
    "osc10-11-fgbg": ESC + "]10;#fff\x07" + ESC + "]11;#000\x07",
    "osc52-clipboard-write": ESC + "]52;c;ZXZpbA==\x07",
    "osc133-shell-integ": ESC + "]133;A\x07",
    "query-da-stdin-inject": ESC + "[c",
    "query-dsr": ESC + "[6n",
    "answerback-enq": "\x05",
    "carriage-return-overwrite": "safe\rEVIL",
    "backspace-erase": "rm -rf\x08\x08 ls",
    "bidi-rlo-override": "user" + RLO + "gnp.txt",
    "bidi-crossed": LRE + LRI + PDF + PDI,
    "bidi-crossed-iso-first": LRI + LRE + PDI + PDF,
    "bidi-unterminated": LRE + "evil",
    "bidi-fsi-unterminated": FSI + "evil",
    "bidi-override-in-embedding": LRE + RLO + "x" + PDF,
    "bidi-extra-close": "x" + PDF,
    "bidi-extra-iso-close": "x" + PDI,
    "mixed-esc-bidi-tag": ESC + "[31m" + RLO + "x" + TAG_A,
    "line-separator": "safe" + LSEP + "EVIL",
    "paragraph-separator": "safe" + PSEP + "EVIL",
    "zero-width-space": "e" + ZWSP + "vil",
    "word-joiner": "e" + WJ + "vil",
    "zwnbsp": "e" + ZWNBSP + "vil",
    "soft-hyphen": "in" + SHY + "voice",
    "invisible-math": "2" + IMATH + "3",
    "hangul-filler": "ev" + HFILL + "il",
    "mongolian-vowel-sep": "ev" + MVS + "il",
    "tag-smuggling": "hi" + TAG_A + TAG_B,
    "vs-supplement-smuggle": "a" + VS_SUP + "b",
    "interlinear": "a" + IAA + "b" + IAT + "c",
    "deprecated-format": "a" + DEPR + "b",
    "lone-surrogate": "pkg" + SURR + "evil",
    "noncharacter-fffe": "a" + NONCHAR + "b",
    "noncharacter-fdd0": "a" + chr(0xFDD0) + "b",
    "noncharacter-astral": "a" + chr(0x1FFFE) + "b",
}

LEGIT = {
    "ascii": "hello world",
    "tab-newline": "a\tb\nc",
    "accented": "café résumé naïve",
    "cjk": "日本語のテキスト",
    "thai": "ภาษาไทยทดสอบ",
    "devanagari": "नमस्ते दुनिया",
    "balanced-lre-pdf": "x" + LRE + "hello" + PDF + "y",
    "nested-lre-lri": LRE + LRI + "inner" + PDI + PDF,
    "arabic": "مرحبا بالعالم",
    "hebrew": "שלום עולם",
    "zwj-emoji": "\U0001f468" + ZWJ + "\U0001f469",
    "zwnj-persian": "پ" + ZWNJ + "د",
    "emoji-vs16-heart": "❤" + VS16,
    "emoji-keycap": "1" + VS16 + "⃣",
    "flag-us": "\U0001f1fa\U0001f1f8",
    "skin-tone": "\U0001f44d\U0001f3fd",
    "bidi-marks": LRM + "a" + RLM + "b" + ALM + "c",
    "balanced-rli-embedded": RLI + LRE + "x" + PDF + PDI,
}


class TestDetectorHasTeeth:
    """The detector must flag a raw dangerous char and clear legitimate text, or
    the neutralisation assertions below would pass vacuously."""

    @pytest.mark.parametrize(
        "raw",
        [
            ESC,
            CSI8,
            "\x7f",
            RLO,
            ZWSP,
            SHY,
            IMATH,
            HFILL,
            MVS,
            VS_SUP,
            SURR,
            NONCHAR,
            TAG_A,
            chr(0xFDD0),
        ],
    )
    def test_flags_raw_dangerous(self, raw):
        assert _has_live_control("x" + raw + "y")

    @pytest.mark.parametrize(
        "clean",
        ["hello world", "café 😀 日本語", "❤" + VS16, "a\tb\nc"],
    )
    def test_passes_clean(self, clean):
        assert not _has_live_control(clean)


class TestTerminalInjectionNeutralized:
    @pytest.mark.parametrize("name", list(ATTACKS))
    def test_attack_is_neutralized(self, name):
        out = sanitize_terminal(ATTACKS[name])
        assert not _has_live_control(out), f"{name} left a live control in {out!r}"
        # sanitised output must always be safe to encode/write (no crash).
        out.encode("utf-8")


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


class TestCsvInjection:
    def test_sanitize_csv_field_neutralizes_formula_and_control(self):
        out = sanitize_csv_field("=cmd|'/c calc'!A1" + ESC + "[31m")
        assert out.startswith("'=")  # formula lead defused
        assert ESC not in out  # control neutralised

    @pytest.mark.parametrize("lead", ["=", "+", "-", "@"])
    def test_every_formula_lead_defused(self, lead):
        assert sanitize_csv_field(lead + "cmd()").startswith("'")

    @pytest.mark.parametrize(
        "prefix", [" ", "\t", chr(0x00A0), chr(0x2007), chr(0x202F), chr(0x3000)]
    )
    def test_whitespace_led_formula_defused(self, prefix):
        # a spreadsheet skips leading (Unicode) whitespace before formula detection
        assert sanitize_csv_field(prefix + "=cmd()").startswith("'")

    @pytest.mark.parametrize("bad", ["-inf", "+inf", "-nan", "+1_0", "-1_000"])
    def test_non_numeric_formula_lead_defused(self, bad):
        # float() accepts these but a spreadsheet would not treat them as a number
        assert sanitize_csv_field(bad).startswith("'")

    @pytest.mark.parametrize("num", ["-3.5", "+2", "-1e5", "+1.2E10", "0", "3.14"])
    def test_genuine_number_kept(self, num):
        assert sanitize_csv_field(num) == num

    def test_non_string_passed_through(self):
        assert sanitize_csv_field(None) is None
        assert sanitize_csv_field(42) == 42
        assert sanitize_csv_field(True) is True
