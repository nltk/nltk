# Natural Language Toolkit: Trojan-Source / bidi neutralisation tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk.termsec.sanitize_terminal defeats Trojan-Source visual reordering
(CVE-2021-42574 / CWE-1007): a bidi override, or any unbalanced directional
formatting, is rendered visible, while balanced Arabic/Hebrew bidi (the
legitimate use) passes through untouched. These tests pin both halves."""

import pytest

from nltk.termsec import sanitize_terminal

RLO = "‮"  # right-to-left override
LRO = "‭"  # left-to-right override
PDF = "‬"  # pop directional formatting
LRE = "‪"
RLE = "‫"
LRI = "⁦"  # left-to-right isolate
RLI = "⁧"
FSI = "⁨"
PDI = "⁩"  # pop directional isolate
RLM = "‏"  # right-to-left mark
LRM = "‎"
ARABIC = "مرحبا"  # marhaba
HEBREW = "שלום"  # shalom


class TestTrojanSourceNeutralised:
    @pytest.mark.parametrize(
        "payload",
        [
            "access_granted" + RLO + "if(admin)",  # unbalanced RLO
            LRO + "gpj.evil" + PDF,  # balanced override still deceptive
            RLO + "reverse me",
            "a" + RLI + "b",  # dangling isolate opener
            "a" + PDI + "b",  # dangling isolate closer
            "a" + PDF + "b",  # dangling embedding closer
            LRE + "no pop",  # dangling embedding opener
        ],
    )
    def test_attacks_are_made_visible(self, payload):
        out = sanitize_terminal(payload)
        # no live bidi override or unbalanced control survives
        for ch in (RLO, LRO):
            assert ch not in out
        # the escaped form is present for whatever was neutralised
        assert "\\u20" in out or "\\u2066" in out or "\\u2069" in out


class TestLegitimateBidiPreserved:
    @pytest.mark.parametrize(
        "text",
        [
            "user " + LRI + ARABIC + PDI + " posted",  # recommended isolate usage
            "x " + RLE + ARABIC + PDF + " y",  # balanced embedding
            ARABIC + RLM + " (2024)",  # a benign direction mark
            ARABIC,
            HEBREW,
            "hello \U0001f600 world",  # emoji / astral plane
            "plain ascii text",
        ],
    )
    def test_balanced_and_plain_text_unchanged(self, text):
        assert sanitize_terminal(text) == text

    def test_control_sequences_still_neutralised(self):
        assert "\x1b" not in sanitize_terminal("\x1b[2Jwipe" + RLO)
