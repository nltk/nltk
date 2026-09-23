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
MUS = chr(0x1D173)  # musical-symbol format control (invisible)

# The codepoints that MUST NOT survive sanitisation, re-derived here independently
# of nltk.termsec so this detector is a real cross-check, not a mirror. Bidi
# embeddings/isolates/marks are included because every ATTACK payload below is
# unbalanced or an override, so the sanitiser escapes them all. This is
# deliberately STRICTER than the sanitiser's spec, which passes balanced
# embeddings/isolates and lone direction marks through for legitimate bidi.
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
        or cp in _BIDI_CONTROLS
        or cp in _ALWAYS_FORMAT
        or 0xE0000 <= cp <= 0xE0FFF
        or 0x1D173 <= cp <= 0x1D17A
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
    "musical-format-smuggle": "note" + MUS + "hidden",
    "khmer-inherent-vowel": "ev" + chr(0x17B4) + "il",
    "reserved-di-2065": "a" + chr(0x2065) + "b",
    "reserved-di-fff0": "a" + chr(0xFFF0) + "b",
    "shorthand-format": "a" + chr(0x1BCA0) + "b",
    "reserved-di-plane14": "a" + chr(0xE01F0) + "b",
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
    "khmer": "ភាសាខ្មែរ",
    "cgj-kept": "a" + chr(0x034F) + "b",
    "mongolian-fvs": chr(0x1820) + chr(0x180B),
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
            MUS,
            chr(0xFDD0),
            chr(0x2065),
            chr(0xFFF0),
            chr(0x17B4),
            chr(0x1BCA0),
            chr(0xE01F0),
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

    def test_exact_safe_primitives_pass_with_type_preserved(self):
        # str() of an EXACT int/float/bool/None cannot carry a payload, so the
        # value and its type are preserved (no munging of numeric cells)
        assert sanitize_csv_field(None) is None
        assert sanitize_csv_field(42) == 42 and type(sanitize_csv_field(42)) is int
        assert sanitize_csv_field(-5) == -5
        assert sanitize_csv_field(3.14) == 3.14
        assert sanitize_csv_field(True) is True
        inf = sanitize_csv_field(float("inf"))
        assert type(inf) is float

    def test_object_with_formula_str_is_defused(self):
        # csv.writer stringifies non-strings AFTER this helper, so a crafted
        # __str__ must be materialised and sanitised HERE, not passed through
        class EvilObj:
            def __str__(self):
                return "=cmd|'/c calc'!A1"

        out = sanitize_csv_field(EvilObj())
        assert isinstance(out, str) and out.startswith("'=")

    def test_lying_int_subclass_is_defused(self):
        # isinstance(int) is True for a subclass, so the fast path must use
        # EXACT types or a lying __str__ smuggles a formula to the writer
        class EvilInt(int):
            def __str__(self):
                return "=2+5+cmd|' /C calc'!A0"

        out = sanitize_csv_field(EvilInt(7))
        assert isinstance(out, str) and out.startswith("'=")

    def test_object_with_control_str_is_neutralised(self):
        class EscObj:
            def __str__(self):
                return "\x1b]0;pwned\x07"

        out = sanitize_csv_field(EscObj())
        assert isinstance(out, str) and not _has_live_control(out)

    def test_raising_str_fails_closed_here(self):
        class Boom:
            def __str__(self):
                raise RuntimeError("no str for you")

        with pytest.raises(RuntimeError):
            sanitize_csv_field(Boom())

    def test_str_subclass_output_is_exactly_str(self):
        # a str subclass is laundered to a plain str by the char-by-char
        # rebuild, so a subclass cannot ride through to the writer
        class Sub(str):
            pass

        assert type(sanitize_csv_field(Sub("=x"))) is str
        assert type(sanitize_terminal(Sub("plain"))) is str


class TestSanitizeIsIdempotent:
    """Escapes are plain printable ASCII, so a second pass must be the identity.
    If it ever is not, an escape is being re-escaped or something dangerous
    survived the first pass and got caught only on the second."""

    @pytest.mark.parametrize("name", list(ATTACKS) + list(LEGIT))
    def test_sanitize_is_idempotent(self, name):
        payload = ATTACKS.get(name, LEGIT.get(name))
        once = sanitize_terminal(payload)
        assert sanitize_terminal(once) == once


class TestNumericBombs:
    """A crafted huge integer must never burn conversion time at the writer:
    CPython's own digit limit (CVE-2020-10735) covers the default config, and
    the chokepoint's ~100,000-digit backstop covers interpreters where that
    limit was disabled. Floats can never bomb (their text is always short)."""

    # bit_length 400_001, far past the backstop; construction is instant
    _BOMB = 1 << 400_000

    def test_bomb_refused_by_every_entry_point(self):
        from nltk.termsec import safe_print

        with pytest.raises(ValueError):
            sanitize_csv_field(self._BOMB)
        with pytest.raises(ValueError):
            sanitize_terminal(self._BOMB)
        with pytest.raises(ValueError):
            safe_print(self._BOMB)

    def test_bomb_refused_even_with_interpreter_guard_disabled(self):
        import sys

        saved = sys.get_int_max_str_digits()
        sys.set_int_max_str_digits(0)
        try:
            with pytest.raises(ValueError):
                sanitize_csv_field(self._BOMB)
            with pytest.raises(ValueError):
                sanitize_terminal(self._BOMB)
        finally:
            sys.set_int_max_str_digits(saved)

    def test_int_subclass_bomb_refused(self):
        class SubInt(int):
            pass

        with pytest.raises(ValueError):
            sanitize_csv_field(SubInt(self._BOMB))

    def test_midsize_int_fails_closed_under_default_guard(self):
        # between the interpreter's 4300-digit limit and our backstop: the
        # exact int passes through and the interpreter guard raises at the
        # conversion, promptly, on every path that stringifies it
        import csv
        import io
        import sys

        saved = sys.get_int_max_str_digits()
        sys.set_int_max_str_digits(4300)
        try:
            big = 10**5000
            out = sanitize_csv_field(big)
            assert out is big  # exact type preserved by the fast path
            with pytest.raises(ValueError):
                csv.writer(io.StringIO()).writerow([out])
            with pytest.raises(ValueError):
                sanitize_terminal(big)
        finally:
            sys.set_int_max_str_digits(saved)

    def test_legit_large_ints_unaffected(self):
        import csv
        import io

        n = 10**100
        assert sanitize_csv_field(n) is n
        buf = io.StringIO()
        csv.writer(buf).writerow([n])
        assert str(n) in buf.getvalue()
        digits = sanitize_terminal(10**4000)
        assert digits == str(10**4000)

    @pytest.mark.parametrize(
        "f", [1e308, 5e-324, -0.0, float("inf"), float("nan"), 3.14, -2.5]
    )
    def test_float_can_never_bomb(self, f):
        out = sanitize_csv_field(f)
        assert type(out) is float
        assert len(str(out)) < 32  # a float's text is bounded, no bomb possible

    def test_long_digit_string_kept_verbatim(self):
        # float() overflows to inf when PARSING, instantly and linearly, so a
        # pure digit run with a sign is accepted as numeric and kept unchanged
        text = "-" + "9" * 5000
        assert sanitize_csv_field(text) == text

    @pytest.mark.parametrize("bad", ["-1.2.3", "+1..2", "+.", "-."])
    def test_many_decimal_points_with_formula_lead_defused(self, bad):
        assert sanitize_csv_field(bad).startswith("'")

    def test_many_decimal_points_without_lead_unchanged(self):
        assert sanitize_csv_field("1.2.3") == "1.2.3"

    def test_decimal_coerced_linearly(self):
        from decimal import Decimal

        out = sanitize_csv_field(Decimal("9" * 10_000))
        assert isinstance(out, str) and len(out) == 10_000
        assert not _has_live_control(out)

    def test_fraction_with_huge_terms_fails_closed(self):
        import sys
        from fractions import Fraction

        saved = sys.get_int_max_str_digits()
        sys.set_int_max_str_digits(4300)
        try:
            with pytest.raises(ValueError):
                sanitize_csv_field(Fraction(10**5000, 3))
        finally:
            sys.set_int_max_str_digits(saved)

    def test_int_subclass_cannot_lie_its_way_past_the_guard(self):
        # the size is read with the unbound builtin int.bit_length, so a
        # subclass overriding bit_length to underreport is still refused:
        # the payload is real even though the object lies
        import sys

        class EvasiveInt(int):
            def bit_length(self):
                return 1

        bomb = EvasiveInt(1 << 400_000)
        assert bomb.bit_length() == 1  # the lie is in place
        with pytest.raises(ValueError):
            sanitize_csv_field(bomb)
        saved = sys.get_int_max_str_digits()
        sys.set_int_max_str_digits(0)
        try:
            with pytest.raises(ValueError):
                sanitize_terminal(bomb)
        finally:
            sys.set_int_max_str_digits(saved)

    def test_guard_consults_no_attacker_attributes(self):
        # the guard must not look anything up on a non-int object, so a
        # crafted bit_length can neither steer it nor become a new crash
        # or code path: the object just takes the ordinary string path
        class Trap:
            def bit_length(self):
                raise RuntimeError("guard should never call this")

            def __str__(self):
                return "harmless"

        assert sanitize_csv_field(Trap()) == "harmless"
        assert sanitize_terminal(Trap()) == "harmless"

    def test_foreign_bignum_takes_linear_string_path(self):
        # a non-int big-number type is not probed; the sanitiser's work is
        # linear in whatever text its own __str__ produces, so there is no
        # superlinear amplification without a real integer
        class Mpz:
            def bit_length(self):
                return 400_001

            def __str__(self):
                return "9" * 50_000

        out = sanitize_csv_field(Mpz())
        assert isinstance(out, str) and len(out) == 50_000

    def test_non_string_sep_still_rejected_by_print(self, capsys):
        # sep/end cannot smuggle an int past the backstop: print itself
        # refuses a non-string sep, so that path fails closed too
        from nltk.termsec import safe_print

        with pytest.raises(TypeError):
            safe_print("a", "b", sep=12345)
