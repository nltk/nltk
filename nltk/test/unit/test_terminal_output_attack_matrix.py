# Natural Language Toolkit: terminal/CSV output injection attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""The twitter json2csv writer end to end over hostile tweets: no live control
byte, bidi override or spreadsheet formula lead reaches the CSV. The
sanitize_terminal and sanitize_csv_field matrices this file once held are in
develop's test_termsec_attack_matrix.py, which now carries every payload they
had, and the Text.concordance sink is pinned by test_print_routing_end_to_end.py.
Nothing is mocked."""

import csv
import io
import json

ESC = chr(0x1B)
RLO = chr(0x202E)  # right-to-left override (Trojan-Source, CVE-2021-42574)


def _has_live_control(s):
    for ch in s:
        c = ord(ch)
        if c in (0x09, 0x0A):
            continue
        if c < 0x20 or c == 0x7F or 0x80 <= c <= 0x9F:
            return True
    return False


class TestEndToEndRealSinks:
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
