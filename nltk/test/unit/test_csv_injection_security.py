# Natural Language Toolkit: CSV-injection guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk exports untrusted tweet data to CSV (nltk.twitter.common.json2csv /
json2csv_entities, nltk.sentiment.util). A CSV cell that begins with = + - @ is
run as a formula when the file is opened in a spreadsheet (CWE-1236), and an
embedded control sequence fires when it is displayed (CWE-150). Every cell is
routed through nltk.termsec.sanitize_csv_field. These tests drive the real
sanitizer and the real json2csv writer (no mocks); only the tweet JSON is a
fixture, which is exactly the untrusted input."""

import csv
import json
import os

import pytest

from nltk.termsec import sanitize_csv_field


class TestSanitizeCsvField:
    @pytest.mark.parametrize(
        "payload",
        [
            '=cmd|"/c calc"!A1',
            "=1+1",
            '=HYPERLINK("http://evil","x")',
            "+cmd",
            "-cmd|'/c calc'",
            "@SUM(1+1)",
            "  =leading_space_formula",
            "\t=leading_tab_formula",
            "=2+5+cmd|' /C calc'!A0",
        ],
    )
    def test_formula_leads_are_neutralised(self, payload):
        out = sanitize_csv_field(payload)
        assert out.startswith("'"), (payload, out)
        # the apostrophe is the only thing prepended; the text itself is intact.
        assert out == "'" + payload

    @pytest.mark.parametrize("number", ["-5", "+3.2", "-1e5", "42", "-0.0", "3.14"])
    def test_genuine_numbers_keep_their_sign(self, number):
        # A leading - / + on a real number is not a formula; do not corrupt it.
        assert sanitize_csv_field(number) == number

    @pytest.mark.parametrize(
        "benign", ["hello world", "RT @user: hi", "normal tweet", "", "café ☕"]
    )
    def test_benign_text_is_unchanged(self, benign):
        assert sanitize_csv_field(benign) == benign

    def test_embedded_control_sequence_is_escaped(self):
        out = sanitize_csv_field("\x1b[2J\x07wipe")
        assert "\x1b" not in out and "\x07" not in out

    def test_non_string_values_pass_through(self):
        # None/int/bool cannot carry a control sequence or a formula lead, and the
        # csv writer renders them safely (None as an empty cell); leave them be.
        assert sanitize_csv_field(None) is None
        assert sanitize_csv_field(12345) == 12345
        assert sanitize_csv_field(True) is True


def _write_tweets(tmp_path, tweets):
    infile = os.path.join(tmp_path, "tweets.json")
    with open(infile, "w", encoding="utf-8") as fh:
        for t in tweets:
            fh.write(json.dumps(t) + "\n")
    return infile


def test_json2csv_neutralises_formula_injection(tmp_path):
    from nltk.twitter.common import json2csv

    tweets = [
        {"id": 1, "text": '=cmd|"/c calc"!A1'},
        {"id": 2, "text": "@SUM(1+1)*cmd"},
        {"id": 3, "text": "a normal tweet"},
        {"id": 4, "text": "-42"},
    ]
    infile = _write_tweets(str(tmp_path), tweets)
    outfile = os.path.join(str(tmp_path), "out.csv")
    with open(infile, encoding="utf-8") as fp:
        json2csv(fp, outfile, ["id", "text"])

    with open(outfile, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    texts = [r[1] for r in rows[1:]]
    assert texts[0].startswith("'="), texts[0]
    assert texts[1].startswith("'@"), texts[1]
    assert texts[2] == "a normal tweet"
    assert texts[3] == "-42"  # legit negative number not corrupted


def test_json2csv_escapes_control_sequences_in_cells(tmp_path):
    from nltk.twitter.common import json2csv

    tweets = [{"id": 1, "text": "\x1b[31mhack\x1b[0m\x07"}]
    infile = _write_tweets(str(tmp_path), tweets)
    outfile = os.path.join(str(tmp_path), "out.csv")
    with open(infile, encoding="utf-8") as fp:
        json2csv(fp, outfile, ["id", "text"])

    raw = open(outfile, encoding="utf-8").read()
    assert "\x1b" not in raw and "\x07" not in raw


def test_json2csv_entities_are_sanitised(tmp_path):
    from nltk.twitter.common import json2csv_entities

    tweets = [
        {
            "id": 7,
            "text": "hi",
            "user": {"name": '=WEBSERVICE("http://evil")'},
            "hashtags": [{"text": "=danger"}],
        }
    ]
    infile = _write_tweets(str(tmp_path), tweets)
    outfile = os.path.join(str(tmp_path), "ent.csv")
    with open(infile, encoding="utf-8") as fp:
        json2csv_entities(
            fp,
            outfile,
            ["id", "text"],
            "hashtags",
            ["text"],
        )
    raw = open(outfile, encoding="utf-8").read()
    # no unescaped formula lead survives on any entity cell
    for line in raw.splitlines()[1:]:
        for cell in next(csv.reader([line]), []):
            assert not (cell[:1] in ("=", "+", "-", "@") and not _isnum(cell)), cell


def _isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
