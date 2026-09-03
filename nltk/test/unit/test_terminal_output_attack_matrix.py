# Natural Language Toolkit: terminal/CSV output injection attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Exhaustive attack corpus for the terminal- and file-output chokepoints
(nltk.termsec). Every known control/escape/bidi/formula injection class is
thrown at sanitize_terminal / sanitize_csv_field and, end to end, at the real
public sinks (Text.concordance, json2csv). A payload "leaks" if any live control
byte, ESC, unbalanced bidi override or spreadsheet formula lead survives; a
benign payload must pass through byte-for-byte. Nothing is mocked."""

import csv
import io
import json

import pytest

from nltk.termsec import sanitize_csv_field, sanitize_terminal

# ---- attack corpus: everything that must be neutralised -------------------

ESC = "\x1b"
BEL = "\x07"
CSI8 = "\x9b"  # 8-bit CSI
OSC8 = "\x9d"  # 8-bit OSC
DCS8 = "\x90"  # 8-bit DCS

ANSI_ATTACKS = [
    ESC + "[2J",  # clear screen
    ESC + "[1;1H",  # cursor home
    ESC + "[31mred" + ESC + "[0m",  # colour
    ESC + "[2K",  # erase line
    ESC + "[?25l",  # hide cursor
    ESC + "]0;pwned" + BEL,  # OSC set window title
    ESC
    + "]8;;https://evil.example"
    + BEL
    + "click"
    + ESC
    + "]8;;"
    + BEL,  # OSC-8 hyperlink
    ESC + "]52;c;ZXZpbA==" + BEL,  # OSC-52 clipboard write
    ESC + "Pq" + ESC + "\\",  # DCS sixel
    CSI8 + "2J",  # 8-bit CSI clear
    OSC8 + "0;title" + BEL,  # 8-bit OSC
    DCS8 + "payload",  # 8-bit DCS
    BEL,  # bell
    "\x08" * 10 + "overwrite",  # backspace overwrite
    "line1\rSPOOF",  # carriage-return overwrite
    "\x0cformfeed",
    "\x7f" + "del",  # DEL
]

# every C0 control except TAB/LF, plus DEL, plus every C1 control
CONTROL_CHARS = (
    [chr(c) for c in range(0x00, 0x20) if c not in (0x09, 0x0A)]
    + [chr(0x7F)]
    + [chr(c) for c in range(0x80, 0xA0)]
)

# Trojan-Source (CVE-2021-42574): overrides + unbalanced directional controls
LRO, RLO, PDF = "\u202d", "\u202e", "\u202c"
LRE, RLE = "\u202a", "\u202b"
LRI, RLI, FSI, PDI = "\u2066", "\u2067", "\u2068", "\u2069"
BIDI_ATTACKS = [
    RLO + "if(admin)",  # dangling override
    LRO + "gpj.evil" + PDF,  # balanced override still deceptive
    "a" + RLI + "b",  # dangling isolate opener
    "a" + PDI + "b",  # dangling isolate closer
    "a" + LRE + "b",  # dangling embedding opener
    "a" + PDF + "b",  # dangling embedding closer
    # classic "commenting-out" PoC (unbalanced isolates)
    'access="user";' + RLI + " admin" + RLO + " only" + PDI,
]

# CSV formula injection (CWE-1236)
FORMULA_ATTACKS = [
    "=1+1",
    "=cmd|'/c calc'!A1",
    '=HYPERLINK("http://evil","x")',
    "@SUM(1+1)*cmd",
    "+cmd",
    "-cmd|'/c calc'",
    "\t=leading_tab",
    "  =leading_space",
    "=2+5+cmd|' /C calc'!A0",
]

# ---- benign corpus: must pass through byte-for-byte ------------------------

BENIGN = [
    "hello world",
    "café ☕ résumé",
    "日本語のテキスト",
    "مرحبا",  # arabic (implicit bidi, no controls)
    "שלום",  # hebrew
    "emoji 😀🎉 \U0001f600",
    "tabs\tand\nnewlines",
    "RT @user: normal tweet #nlp",
    "user " + LRI + "مرحبا" + PDI + " posted",  # balanced isolate
    "x " + RLE + "שלום" + PDF + " y",  # balanced embedding
]


def _has_live_control(s):
    for ch in s:
        c = ord(ch)
        if c in (0x09, 0x0A):
            continue
        if c < 0x20 or c == 0x7F or 0x80 <= c <= 0x9F:
            return True
    return False


class TestSanitizeTerminalMatrix:
    @pytest.mark.parametrize("payload", ANSI_ATTACKS + CONTROL_CHARS + BIDI_ATTACKS)
    def test_no_live_control_or_override_survives(self, payload):
        out = sanitize_terminal(payload)
        assert not _has_live_control(out), repr(out)
        assert LRO not in out and RLO not in out  # overrides always neutralised

    @pytest.mark.parametrize("payload", BENIGN)
    def test_benign_passes_through_unchanged(self, payload):
        assert sanitize_terminal(payload) == payload


class TestSanitizeCsvMatrix:
    @pytest.mark.parametrize("payload", FORMULA_ATTACKS)
    def test_formula_leads_neutralised(self, payload):
        out = sanitize_csv_field(payload)
        assert out.startswith("'"), repr(out)

    @pytest.mark.parametrize("payload", ANSI_ATTACKS + BIDI_ATTACKS)
    def test_csv_inherits_terminal_protection(self, payload):
        out = sanitize_csv_field(payload)
        assert not _has_live_control(out) and LRO not in out and RLO not in out

    @pytest.mark.parametrize("number", ["-42", "+3.14", "-1e5", "0"])
    def test_numbers_preserved(self, number):
        assert sanitize_csv_field(number) == number


class TestEndToEndRealSinks:
    def test_concordance_over_hostile_corpus_does_not_leak(self, capsys):
        from nltk.text import Text

        toks = ("the " + ESC + "[2J" + RLO + "evil the good the bad the end").split()
        Text(toks * 3).concordance("the", width=79, lines=5)
        out = capsys.readouterr().out
        assert not _has_live_control(out) and RLO not in out

    def test_json2csv_over_hostile_tweets_does_not_leak(self, tmp_path):
        from nltk.twitter.common import json2csv

        tweets = [
            {"id": 1, "text": "=cmd|'/c calc'!A1"},
            {"id": 2, "text": ESC + "[31m" + RLO + "spoof"},
            {"id": 3, "text": "@SUM(1)"},
        ]
        infile = tmp_path / "t.json"
        with open(infile, "w", encoding="utf-8") as fh:
            for t in tweets:
                fh.write(json.dumps(t) + "\n")
        outfile = tmp_path / "o.csv"
        with open(infile, encoding="utf-8") as fp:
            json2csv(fp, str(outfile), ["id", "text"])
        raw = outfile.read_text(encoding="utf-8")
        assert not _has_live_control(raw) and RLO not in raw
        # every data cell that led with a formula char is now apostrophe-guarded
        for row in csv.reader(io.StringIO(raw)):
            for cell in row:
                assert cell[:1] not in ("=", "@") or cell.startswith("'")
