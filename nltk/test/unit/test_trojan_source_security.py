# Natural Language Toolkit: Trojan-Source / bidi neutralisation tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``nltk.termsec.sanitize_terminal`` defeats Trojan-Source visual reordering
(CVE-2021-42574 / CWE-1007). Its guarantee, and what these tests pin:

* a directional OVERRIDE (LRO/RLO) is escaped ALWAYS - it is the only control
  that reverses strong-directional characters (the filename/comment spoof), and
  it never has a legitimate use in a plain value;
* any UNBALANCED or CROSSED directional formatting is escaped in full - malformed
  nesting cannot be legitimate bidi;
* BALANCED embeddings/isolates and the neutral direction marks pass through so
  legitimate mixed-direction text (an LTR run inside RTL, a bracketed number,
  Arabic/Hebrew) is not corrupted. A balanced isolate cannot reverse strong
  characters, so the character-reversal spoof stays closed by the override rule.

Every bidi control is written as ``chr(0x...)`` so the source cannot be silently
reordered by an editor viewing this file, and ``_bidi_neutralised`` is derived
independently of nltk.termsec so a regression is caught rather than mirrored."""

import pytest

from nltk.termsec import _bidi_is_balanced, sanitize_terminal

LRE, RLE, PDF = chr(0x202A), chr(0x202B), chr(0x202C)
LRO, RLO = chr(0x202D), chr(0x202E)
LRI, RLI, FSI, PDI = chr(0x2066), chr(0x2067), chr(0x2068), chr(0x2069)
LRM, RLM, ALM = chr(0x200E), chr(0x200F), chr(0x061C)
ARABIC = "مرحبا"  # marhaba
HEBREW = "שלום"  # shalom

_BIDI_CPS = {
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


def _bidi_neutralised(s):
    return not any(ord(ch) in _BIDI_CPS for ch in s)


# Override-driven spoofs (character reversal / comment hiding). The override is
# escaped unconditionally, so it never survives - even when its own nesting is
# balanced (the residual harmless PDF is a no-op once the override is gone).
OVERRIDE_ATTACKS = [
    "value = 42" + RLO + " ;)tini_lave(",  # reversed tail hides real code
    "name = '" + RLO + "'; drop_all()  #",  # stretched-string template
    "call" + LRO + ")(rekcatta_" + PDF + "()",  # invisible-function template
    "invoice" + RLO + "cod.exe",  # filename spoof -> "invoiceexe.doc"
    "photo_high" + RLO + "gpj.js",
    "resume_" + RLO + "fdp.scr",
    RLO + "reverse me",
    "start" + RLO + "end",
    LRE + RLO + "x" + PDF,  # override inside an embedding
    "a" + LRI + RLO + "x" + PDI,  # override inside an isolate
]

# Malformed nesting: unbalanced, crossed, or dangling. None can be legitimate, so
# EVERY bidi control in these is escaped.
MALFORMED_ATTACKS = [
    "if " + RLI + "admin: return  # early",  # dangling isolate opener
    LRE + "no pop",
    RLE + "no pop",
    "no push" + PDF,
    LRI + "no pop",
    RLI + "no pop",
    FSI + "no pop",
    "no push" + PDI,
    LRE + LRI + PDF + PDI,  # crossed embedding/isolate
    LRI + LRE + PDI + PDF,
    RLE + RLI + PDF + PDI,
    LRE + PDI,  # wrong closer kind
    LRI + PDF,
    LRE + "a" + PDF + PDF,  # extra closer
]


class TestOverrideAttacksNeutralised:
    @pytest.mark.parametrize("payload", OVERRIDE_ATTACKS)
    def test_no_override_survives(self, payload):
        out = sanitize_terminal(payload)
        assert RLO not in out and LRO not in out, f"override survived in {out!r}"
        out.encode("utf-8")


class TestMalformedBidiFullyNeutralised:
    @pytest.mark.parametrize("payload", MALFORMED_ATTACKS)
    def test_fully_neutralised(self, payload):
        out = sanitize_terminal(payload)
        assert _bidi_neutralised(out), f"live bidi control survived in {out!r}"
        out.encode("utf-8")

    def test_control_and_bidi_both_neutralised(self):
        out = sanitize_terminal("\x1b[2Jwipe" + RLO + "evil")
        assert "\x1b" not in out and RLO not in out


class TestLegitimateBidiPreserved:
    @pytest.mark.parametrize(
        "text",
        [
            "user " + LRI + ARABIC + PDI + " posted",  # recommended isolate usage
            "x " + RLE + ARABIC + PDF + " y",  # balanced embedding
            "total " + LRI + "42 USD" + PDI + " paid",  # LTR number inside a run
            LRE + LRI + "deep" + PDI + PDF,  # balanced nesting
            ARABIC + RLM + " (2024)",  # a benign direction mark
            "price " + ALM + "100",  # arabic-letter mark for digit shaping
            LRM + "a" + RLM + "b",  # bare marks (no embeddings) stay
            ARABIC,
            HEBREW,
            ARABIC + " " + HEBREW,
            "hello \U0001f600 world",  # emoji / astral plane
            "plain ascii text",
        ],
    )
    def test_balanced_and_plain_text_unchanged(self, text):
        assert sanitize_terminal(text) == text


class TestBidiBalanceLogic:
    @pytest.mark.parametrize(
        "text",
        [
            "",
            "plain",
            LRE + "a" + PDF,
            RLE + "a" + PDF,
            LRI + "a" + PDI,
            LRE + LRI + "a" + PDI + PDF,
            RLI + LRE + "x" + PDF + PDI,
            LRM + RLM + ALM,  # marks do not open/close nesting
        ],
    )
    def test_balanced(self, text):
        assert _bidi_is_balanced(text)

    @pytest.mark.parametrize(
        "text",
        [
            LRE,
            PDF,
            PDI,
            LRE + LRI + PDF + PDI,  # crossed
            LRI + LRE + PDI + PDF,  # crossed
            LRE + PDI,  # wrong closer kind
            LRI + PDF,
            LRE + "a" + PDF + PDF,  # extra closer
        ],
    )
    def test_unbalanced(self, text):
        assert not _bidi_is_balanced(text)


class TestDetectorHasTeeth:
    def test_raw_override_flagged(self):
        assert not _bidi_neutralised("a" + RLO + "b")

    def test_clean_passes(self):
        assert _bidi_neutralised("plain ascii and café")


class TestSanitiserSourcesAreTrojanSourceClean:
    """The sanitiser and its harness spell every bidi control and invisible
    character as an escape. A literal one in these sources would trip the
    very class they defend against (CVE-2021-42574) inside the security
    code itself, and tooling that decodes escapes has produced exactly that
    once; so the sources are scanned, with the detector's teeth checked."""

    _SUSPECT = frozenset(
        set(range(0x202A, 0x202F))
        | set(range(0x2066, 0x206A))
        | set(range(0x200B, 0x2010))
        | set(range(0x2060, 0x2065))
        | {0xFEFF, 0x00A0, 0x3000, 0x00AD, 0x2028, 0x2029, 0x061C, 0x180E}
    )

    @classmethod
    def _literal_suspects(cls, text):
        return sorted({f"U+{ord(ch):04X}" for ch in text if ord(ch) in cls._SUSPECT})

    def test_detector_has_teeth(self):
        assert self._literal_suspects("x" + chr(0x202E) + chr(0xFEFF)) == [
            "U+202E",
            "U+FEFF",
        ]
        assert self._literal_suspects("plain \\u202e escape text") == []

    @pytest.mark.parametrize(
        "relative",
        [
            "termsec.py",
            "csvsec.py",
            "test/unit/test_termsec_security.py",
            "test/unit/test_termsec_attack_matrix.py",
            "test/unit/test_trojan_source_security.py",
            "test/unit/test_print_injection_sinks.py",
            "test/unit/test_csvsec_writer.py",
        ],
    )
    def test_source_has_no_literal_bidi_or_invisible_characters(self, relative):
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / relative).read_text(
            encoding="utf-8"
        )
        assert self._literal_suspects(source) == [], relative
